import "./globals.css";
import "../components/institutional-brand.css";
import InstitutionalMasthead from "../components/InstitutionalMasthead";
export const metadata = {
  title: "Salud y Odontología | Universidad Modelo",
  icons: { icon: [{url:"/images/Modelo.jpg",type:"image/jpeg"}], apple: "/images/Modelo.jpg" },
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
        <InstitutionalMasthead />
        {children}
      </body>
    </html>
  );
}
