import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./features/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef4ff",
          100: "#d9e6ff",
          200: "#b8d0ff",
          300: "#8fb0ff",
          400: "#5a83ee",
          500: "#2f5fe0",
          600: "#1f47c0",
          700: "#1a3a9c",
          800: "#16307d",
          900: "#101f52",
        },
        accent: {
          50: "#fbf3e9",
          100: "#f6e4cd",
          200: "#eec79b",
          300: "#e3a862",
          400: "#d98b34",
          500: "#c2701a",
          600: "#a15612",
          700: "#7d4210",
        },
        ink: {
          DEFAULT: "#12100c",
          800: "#221f18",
          700: "#37322a",
        },
        paper: {
          DEFAULT: "#f4f1ea",
          100: "#efeadf",
          200: "#e5ded0",
          300: "#d8cfbd",
        },
      },
      boxShadow: {
        card: "0 1px 2px rgba(18,16,12,0.04), 0 10px 30px -18px rgba(18,16,12,0.25)",
        lift: "0 2px 6px rgba(18,16,12,0.06), 0 24px 50px -24px rgba(18,16,12,0.35)",
      },
      fontFamily: {
        display: ["var(--font-display)", "ui-serif", "Georgia", "serif"],
        mono: ["var(--font-mono)", "ui-monospace", "SFMono-Regular", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
