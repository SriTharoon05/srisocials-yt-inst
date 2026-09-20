import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App.jsx";
import LegalPage, {legalPagePath} from "./LegalPage.jsx";
const policyPath = legalPagePath(window.location.pathname);
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      {policyPath ? <LegalPage path={policyPath}/> : <App />}
    </BrowserRouter>
  </React.StrictMode>
);
