/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0b0f19",
        surface: "#111827",
        "surface-raised": "#1f2937",
        "border-color": "#374151",
      },
      fontFamily: {
        mono: ['"Fira Code"', 'Consolas', 'Monaco', 'Courier New', 'monospace'],
      },
    },
  },
  plugins: [],
}
