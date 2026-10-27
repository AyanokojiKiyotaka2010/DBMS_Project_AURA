/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: ["./src/**/*.{js,jsx,ts,tsx}", "./public/index.html"],
  theme: {
    extend: {
      fontFamily: {
        serif: ['"Cormorant Garamond"', "Iowan Old Style", "Georgia", "serif"],
        sans: ["Outfit", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 4px)",
        sm: "calc(var(--radius) - 8px)",
      },
      colors: {
        paper: {
          DEFAULT: "#F9F8F6",
          card: "#FFFFFF",
          sidebar: "#F4F2EC",
        },
        ink: {
          DEFAULT: "#2D2B2A",
          2: "#5C5856",
          3: "#8A8581",
        },
        edge: {
          light: "#EAE5D9",
          DEFAULT: "#D1CCC0",
          dark: "#A39E93",
        },
        brand: {
          DEFAULT: "#D95D39",
          hover: "#BF4E2D",
          deep: "#2A4747",
          gold: "#E8B255",
        },
        role: {
          "cr-bg": "#FEEBC8",
          "cr-text": "#C05621",
          "cr-border": "#FBD38D",
          "dcr-bg": "#FEFCBF",
          "dcr-text": "#975A16",
          "dcr-border": "#FAF089",
          "prof-bg": "#C6F6D5",
          "prof-text": "#22543D",
          "prof-border": "#9AE6B4",
          "alumni-bg": "#E9D8FD",
          "alumni-text": "#44337A",
          "alumni-border": "#D6BCFA",
          "senior-bg": "#BEE3F8",
          "senior-text": "#2C5282",
          "senior-border": "#90CDF4",
          "student-bg": "#E2E8F0",
          "student-text": "#2D3748",
          "student-border": "#CBD5E0",
        },
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
      },
      keyframes: {
        "accordion-down": { from: { height: "0" }, to: { height: "var(--radix-accordion-content-height)" } },
        "accordion-up": { from: { height: "var(--radix-accordion-content-height)" }, to: { height: "0" } },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
      },
      boxShadow: {
        clay: "0 4px 20px -8px rgba(42,71,71,0.10)",
        "clay-lg": "0 12px 40px -14px rgba(42,71,71,0.18)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
