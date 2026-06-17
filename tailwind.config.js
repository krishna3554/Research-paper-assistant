/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"IBM Plex Sans Condensed"', "ui-sans-serif", "sans-serif"],
        serif: ['"Newsreader"', "Georgia", "serif"]
      },
      boxShadow: {
        panel: "0 24px 80px rgba(0, 0, 0, 0.36)"
      }
    }
  },
  plugins: []
};
