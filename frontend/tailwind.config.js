/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,jsx,ts,tsx}", "./public/index.html"],
  theme: {
    extend: {
      colors: {
        obsidian: "#0A0A0A",
        surface: "#121212",
        elevated: "#1A1A1A",
        gold: {
          DEFAULT: "#D4AF37",
          hover: "#E5C158",
        },
      },
      fontFamily: {
        display: ["Outfit", "sans-serif"],
        body: ["Manrope", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      boxShadow: {
        goldGlow: "0 0 40px -8px rgba(212, 175, 55, 0.35)",
      },
      keyframes: {
        shimmer: {
          "0%": { backgroundPosition: "-1000px 0" },
          "100%": { backgroundPosition: "1000px 0" },
        },
      },
      animation: {
        shimmer: "shimmer 2.4s linear infinite",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
