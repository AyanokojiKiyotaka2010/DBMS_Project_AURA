import React from "react";
import ReactDOM from "react-dom/client";
import "./index.css";
import "./App.css";
import { BrowserRouter } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { Toaster } from "sonner";
import App from "./App";

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <AuthProvider>
      <BrowserRouter>
        <App />
        <Toaster
          position="bottom-right"
          richColors
          closeButton
          toastOptions={{
            style: {
              fontFamily: "'Outfit', ui-sans-serif, system-ui",
              border: "1px solid #EAE5D9",
              boxShadow: "0 4px 20px -4px rgba(42,71,71,0.12)",
            },
          }}
        />
      </BrowserRouter>
    </AuthProvider>
  </React.StrictMode>
);
