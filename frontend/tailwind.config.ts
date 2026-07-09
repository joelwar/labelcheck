import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#1f2933",
        mist: "#f5f7fa",
        line: "#d9e2ec",
        teal: "#0f766e",
        gold: "#a16207",
        rose: "#b42318"
      }
    }
  },
  plugins: []
};

export default config;
