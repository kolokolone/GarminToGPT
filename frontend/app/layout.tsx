import type { Metadata } from "next";
import "../styles/globals.css";

export const metadata: Metadata = {
  title: "GarminToGPT",
  description: "Pont local sécurisé entre Garmin MCP et ChatGPT.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}
