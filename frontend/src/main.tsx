import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { cowriterApi } from "./services/backend/cowriterApi";
import "./styles.css";

createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App api={cowriterApi} />
  </React.StrictMode>,
);
