import type { Metadata } from "next";

import { AuthProvider } from "@/features/auth/auth-context";
import "./globals.css";

export const metadata: Metadata = {
  title: "AutoBid Intelligence",
  description:
    "Decision-support platform for UK motor dealers buying at auction. Estimates safe and absolute maximum bids, profit, ROI and risk. Not a guarantee of profit.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en-GB">
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
