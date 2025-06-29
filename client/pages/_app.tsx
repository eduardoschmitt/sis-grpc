import "primereact/resources/themes/saga-blue/theme.css";
import "primereact/resources/primereact.min.css";   
import "primeicons/primeicons.css";                      
import "primeflex/primeflex.css";       
import "../styles/globals.css";  

import type { AppProps } from "next/app";

export default function App({ Component, pageProps }: AppProps) {
  return <Component {...pageProps} />;
}
