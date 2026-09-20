import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import LegalPage, {legalPagePath} from "./LegalPage.jsx";
const policyPath = legalPagePath(window.location.pathname);
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    {policyPath ? <LegalPage path={policyPath}/> : <App />}
  </React.StrictMode>
);
