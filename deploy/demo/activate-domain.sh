#!/usr/bin/env bash
# Administrator-reviewed activation of ONLY plansaludmodelo.online.
set -Eeuo pipefail
[[ $EUID -eq 0 ]] || { echo 'Ejecute este archivo con sudo desde su terminal; no comparta contraseñas.' >&2; exit 1; }
echo 'Salud Modelo: activador v3 (espera recarga de Nginx y valida HTTPS local/público).'
BASE=/home/gaibarra/plandetrabajo/deploy/demo
SITE=/etc/nginx/sites-available/salud-modelo-demo.conf
LINK=/etc/nginx/sites-enabled/salud-modelo-demo.conf
CERT=/etc/letsencrypt-salud-modelo-demo/live/plansaludmodelo.online/fullchain.pem
CERT_KEY=/etc/letsencrypt-salud-modelo-demo/live/plansaludmodelo.online/privkey.pem
exec 9>/run/lock/salud-modelo-demo-domain.lock
flock -n 9 || { echo 'Ya hay una activación propia en curso.' >&2; exit 1; }
for target in "$SITE" "$LINK" /etc/systemd/system/salud-modelo-demo-cert-renew.service /etc/systemd/system/salud-modelo-demo-cert-renew.timer; do
  [[ ! -e $target && ! -L $target ]] || { echo "Se conserva el archivo existente: $target. Solicite revisión antes de continuar." >&2; exit 1; }
done
/usr/sbin/nginx -t
/usr/sbin/nginx -T 2>/dev/null | python3 -c 'import re,sys; s=sys.stdin.read(); sys.exit(1 if re.search(r"\bserver_name\s+[^;]*\bplansaludmodelo\.online\b",s) else 0)' || { echo 'El dominio ya está configurado. No se sobrescribirá.' >&2; exit 1; }
getent ahostsv4 plansaludmodelo.online | awk '{print $1}' | sort -u | grep -qx '194.113.64.91' || { echo 'Revise DNS antes de activar.' >&2; exit 1; }
[[ $(curl --noproxy '*' --fail --silent --max-time 10 -H 'Host: plansaludmodelo.online' http://127.0.0.1:3117/health) == salud-modelo-demo ]] || { echo 'La aplicación propia no responde.' >&2; exit 1; }
created=0
complete=0
challenge_file=
rollback() {
  result=$?
  if [[ -n $challenge_file ]]; then rm -f -- "$challenge_file"; fi
  if [[ $created == 1 && $complete == 0 ]]; then
    echo 'No se completó la activación. Retirando exclusivamente el sitio nuevo.' >&2
    rm -f -- "$LINK" "$SITE"
    if /usr/sbin/nginx -t; then /usr/bin/systemctl reload nginx; fi
  fi
  exit "$result"
}
trap rollback EXIT
if [[ -s $CERT && -s $CERT_KEY ]] &&
   openssl x509 -in "$CERT" -noout -checkhost plansaludmodelo.online >/dev/null &&
   openssl x509 -in "$CERT" -noout -checkend 86400 >/dev/null; then
  echo 'Certificado propio vigente encontrado; se reutiliza sin solicitar otro a Certbot.'
else
  install -m 644 "$BASE/domain-http.conf" "$SITE"
  created=1
  ln -s "$SITE" "$LINK"
  /usr/sbin/nginx -t
  /usr/bin/systemctl reload nginx
  challenge_file=$(mktemp "$BASE/acme/.well-known/acme-challenge/salud-preflight-XXXXXX")
  chmod 644 "$challenge_file"
  printf 'salud-modelo-acme-ok\n' > "$challenge_file"
  response=
  for attempt in {1..30}; do
    response=$(curl --noproxy '*' --fail --silent --max-time 3 \
      --resolve plansaludmodelo.online:80:127.0.0.1 \
      "http://plansaludmodelo.online/.well-known/acme-challenge/${challenge_file##*/}") || response=
    [[ $response == salud-modelo-acme-ok ]] && break
    sleep 0.5
  done
  [[ $response == salud-modelo-acme-ok ]] || {
    echo 'El desafío HTTP no llega al sitio nuevo; revise Nginx antes de pedir un certificado.' >&2
    exit 1
  }
  rm -f -- "$challenge_file"
  challenge_file=
  # New isolated Certbot directories: no existing certificates or renewal jobs changed.
  /usr/bin/certbot certonly --webroot -w "$BASE/acme" -d plansaludmodelo.online \
    --cert-name plansaludmodelo.online --non-interactive --agree-tos --register-unsafely-without-email \
    --config-dir /etc/letsencrypt-salud-modelo-demo \
    --work-dir /var/lib/letsencrypt-salud-modelo-demo \
    --logs-dir /var/log/letsencrypt-salud-modelo-demo
  [[ -s $CERT && -s $CERT_KEY ]] || { echo 'Certbot terminó sin dejar el certificado esperado.' >&2; exit 1; }
fi
install -m 644 "$BASE/domain-https.conf" "$SITE"
if [[ $created == 0 ]]; then
  created=1
  ln -s "$SITE" "$LINK"
fi
/usr/sbin/nginx -t
/usr/bin/systemctl reload nginx
# systemctl reload only signals the master: existing workers can still serve
# their old default certificate for a short time. Wait for the new vhost.
response=
for attempt in {1..30}; do
  response=$(curl --noproxy '*' --fail --silent --max-time 3 \
    --resolve plansaludmodelo.online:443:127.0.0.1 \
    https://plansaludmodelo.online/health) || response=
  [[ $response == salud-modelo-demo ]] && break
  sleep 0.5
done
[[ $response == salud-modelo-demo ]] || {
  echo 'Tras esperar la recarga, Nginx local aún no sirve el certificado/sitio nuevo.' >&2
  exit 1
}
response=
for attempt in {1..20}; do
  response=$(curl --noproxy '*' --fail --silent --max-time 3 \
    https://plansaludmodelo.online/health) || response=
  [[ $response == salud-modelo-demo ]] && break
  sleep 0.5
done
[[ $response == salud-modelo-demo ]] || {
  echo 'El dominio público aún no sirve la aplicación de demostración.' >&2
  exit 1
}
complete=1
install -m 644 "$BASE/salud-modelo-demo-cert-renew.service" /etc/systemd/system/salud-modelo-demo-cert-renew.service
install -m 644 "$BASE/salud-modelo-demo-cert-renew.timer" /etc/systemd/system/salud-modelo-demo-cert-renew.timer
/usr/bin/systemctl daemon-reload
/usr/bin/systemctl enable --now salud-modelo-demo-cert-renew.timer
echo 'Sitio HTTPS activado. Continuar con la comprobación de acceso y el ensayo de la demostración.'
