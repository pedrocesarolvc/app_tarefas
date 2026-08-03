import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Configuração mínima: só o plugin do React (JSX + Fast Refresh durante o
// desenvolvimento). Nenhuma configuração de PWA (service worker,
// manifest) está aqui de propósito -- isso é conteúdo das Etapas 5 e 7 da
// documentação (docs/documentacao.md), que ainda não foram escritas.
export default defineConfig({
  plugins: [react()],
  server: {
    // O backend (Etapa 1.5, FastAPI) roda por padrão em outra porta; um
    // proxy de /api evita problemas de CORS durante o desenvolvimento
    // local, encaminhando as chamadas do frontend para o backend sem
    // expor a porta 8000 diretamente ao código do navegador.
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (caminho) => caminho.replace(/^\/api/, ""),
      },
    },
  },
});
