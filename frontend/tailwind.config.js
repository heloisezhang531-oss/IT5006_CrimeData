/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#0f172a",
      },
      boxShadow: {
        glass: "0 10px 40px rgba(15, 23, 42, 0.18)",
      },
      backgroundImage: {
        aurora: "radial-gradient(circle at 20% 20%, rgba(56, 189, 248, 0.35), transparent 40%), radial-gradient(circle at 80% 0%, rgba(99, 102, 241, 0.25), transparent 45%), linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%)",
      },
    },
  },
  plugins: [],
};
