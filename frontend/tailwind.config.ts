import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#171717",
        paper: "#f7f4ef",
        moss: "#3f6f5b",
        coral: "#d85c4a",
        skyglass: "#dbeafe"
      }
    }
  },
  plugins: []
};

export default config;
