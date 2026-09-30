import "./globals.css";
export const metadata = {
  title: "Salud y Odontología | Universidad Modelo",
  description: "Servicios y gestión académica de las Escuelas de Salud y Odontología",
};
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>
        {process.env.NEXT_PUBLIC_DEMO_MODE === "1" && (
          <aside style={{background:"#fff3cd",color:"#493800",padding:"10px 20px",textAlign:"center",fontWeight:600}}>
            DEMOSTRACIÓN · Datos ficticios de Odontología · No registrar información de pacientes
          </aside>
        )}
        {children}
      </body>
    </html>
  );
}
