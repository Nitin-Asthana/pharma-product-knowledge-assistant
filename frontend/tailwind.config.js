/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef4fb",
          100: "#d7e4f4",
          200: "#b0c9e8",
          300: "#82a8d8",
          400: "#5183c4",
          500: "#2f66ad",
          600: "#204f8f",
          700: "#1b3f72",
          800: "#183456",
          900: "#0f233c",
        },
        ink: {
          900: "#0f172a",
          700: "#334155",
          500: "#64748b",
          300: "#cbd5e1",
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "Segoe UI",
          "system-ui",
          "-apple-system",
          "sans-serif",
        ],
      },
      boxShadow: {
        card: "0 1px 2px rgba(15,23,42,0.04), 0 4px 12px rgba(15,23,42,0.06)",
      },
    },
  },
  plugins: [],
};
