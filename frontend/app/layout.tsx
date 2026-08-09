import "./globals.css";
import { Providers } from "@/components/Providers";
import { NavBar } from "@/components/NavBar";

export const metadata = {
  title: "GovAI — AI DAO Governance Copilot",
  description: "Summarize, score, and vote on cross-Layer DAO proposals with AI.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <NavBar />
          <main className="container">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
