/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#fdf6ee',
          100: '#f8e4cc',
          500: '#b4762c',
          600: '#94601f',
          700: '#734a17',
          900: '#3d2709',
        },
      },
    },
  },
  plugins: [],
}
