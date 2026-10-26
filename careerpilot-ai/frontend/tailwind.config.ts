import type { Config } from "tailwindcss";
const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}", "./components/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: { extend: { colors: { ink: "#14213D", brand: "#4F46E5", canvas: "#F7F8FC" }, boxShadow: { soft: "0 8px 28px rgba(22, 34, 67, 0.06)" } } },
  plugins: [],
};
export default config;
