/**
 * Service worker (Etapa 5.7 / 7.3): recebe o push mesmo com o app
 * fechado, e trata o clique na notificação para abrir o app já no
 * cartão certo — as duas responsabilidades do v1 ("sem ele, Web Push
 * não existe").
 *
 * Fica em public/, servido como está, sem passar pelo bundler do Vite
 * (ver frontend/vite.config.ts): é pouco código, não importa nada do
 * resto do app, e um service worker precisa de uma URL estável na raiz
 * do site para poder controlar a origem inteira — jogar isso para
 * dentro de src/ e empacotar via Vite pediria um segundo ponto de
 * entrada de build só para um arquivo que não se beneficia disso.
 */

self.addEventListener("install", () => {
  // Não espera as abas antigas fecharem para assumir -- não há nada
  // "antigo" para preservar num app pessoal de uma usuária só.
  self.skipWaiting();
});

self.addEventListener("activate", (evento) => {
  evento.waitUntil(self.clients.claim());
});

self.addEventListener("push", (evento) => {
  if (!evento.data) return;
  // O formato exato é o que backend/worker/push.py monta:
  // {"titulo": ..., "corpo": ..., "url": ...} -- ver o comentário lá
  // sobre por que a URL viaja junto (Etapa 5.7: abrir no cartão certo).
  const dados = evento.data.json();
  evento.waitUntil(
    self.registration.showNotification(dados.titulo, {
      body: dados.corpo,
      data: { url: dados.url || "/" },
    })
  );
});

self.addEventListener("notificationclick", (evento) => {
  evento.notification.close();
  const url = (evento.notification.data && evento.notification.data.url) || "/";

  evento.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((listaDeClientes) => {
      // Se o app já estiver aberto numa aba, reaproveita ela (navegando
      // para o cartão certo) em vez de abrir uma segunda aba -- mais
      // parecido com o comportamento normal de um app instalado.
      for (const cliente of listaDeClientes) {
        if ("focus" in cliente) {
          if ("navigate" in cliente) cliente.navigate(url);
          return cliente.focus();
        }
      }
      return self.clients.openWindow(url);
    })
  );
});
