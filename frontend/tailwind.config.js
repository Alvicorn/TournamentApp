/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        competitorA: "#dc2626",
        competitorB: "#2563eb",
      },
    },
  },
  plugins: [],
};
