/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        'zen-cream': '#F5F5F1',
        'zen-ink': '#1A1A1A',
        'tori-red': '#C8102E',
      },
    },
  },
  plugins: [],
}
