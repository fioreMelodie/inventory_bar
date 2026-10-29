/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#eef8f4',
          100: '#d8eee5',
          500: '#268468',
          600: '#176b52',
          700: '#10533f',
          900: '#10372c',
        },
      },
    },
  },
  plugins: [],
}
