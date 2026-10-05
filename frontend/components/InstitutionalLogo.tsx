import Image from "next/image";
/** Original institutional asset; preserve its proportions, colors and white ground. */
export default function InstitutionalLogo({size="standard"}:{size?:"compact"|"standard"|"report"}) {
 return <Image className={`institutional-logo institutional-logo-${size}`} src="/images/Modelo.jpg" alt="Logo institucional de Modelo" width={224} height={225} loading="eager" unoptimized />;
}
