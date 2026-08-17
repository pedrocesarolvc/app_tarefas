import { useState, type FormEvent } from "react";
import { auth, ErroDeApi } from "../api/cliente";
import type { Usuario } from "../api/tipos";
import "../estilos/login.css";

/** Login e cadastro num formulário só (Etapa 1.4: "login simples"). Não
 * há tela de "esqueci minha senha" nem confirmação por e-mail -- não
 * existe no backend, e inventar aqui seria prometer algo que a API não
 * cumpre. */
export default function TelaLogin({ aoEntrar }: { aoEntrar: (usuario: Usuario) => void }) {
  const [modo, setModo] = useState<"entrar" | "registrar">("entrar");
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function aoSubmeter(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    setEnviando(true);
    try {
      if (modo === "registrar") {
        await auth.registrar(email, senha);
      }
      const usuario = await auth.login(email, senha);
      aoEntrar(usuario);
    } catch (erroCapturado) {
      setErro(erroCapturado instanceof ErroDeApi ? erroCapturado.message : "Não foi possível entrar.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="tela-login">
      <form className="tela-login__cartao" onSubmit={aoSubmeter}>
        <h1 className="tela-login__titulo">Kanban com tempo</h1>
        <p className="tela-login__subtitulo">
          {modo === "entrar" ? "Entre para ver seus quadros." : "Crie uma conta para começar."}
        </p>

        <label className="tela-login__campo">
          E-mail
          <input
            type="email"
            required
            value={email}
            onChange={(evento) => setEmail(evento.target.value)}
            autoFocus
          />
        </label>

        <label className="tela-login__campo">
          Senha
          <input type="password" required minLength={8} value={senha} onChange={(evento) => setSenha(evento.target.value)} />
        </label>

        {erro && <p className="tela-login__erro">{erro}</p>}

        <button type="submit" className="tela-login__botao" disabled={enviando}>
          {enviando ? "Um instante..." : modo === "entrar" ? "Entrar" : "Criar conta e entrar"}
        </button>

        <button
          type="button"
          className="tela-login__alternar"
          onClick={() => setModo((atual) => (atual === "entrar" ? "registrar" : "entrar"))}
        >
          {modo === "entrar" ? "Ainda não tenho conta" : "Já tenho conta"}
        </button>
      </form>
    </div>
  );
}
