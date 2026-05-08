import { ThemeToggle } from "../../../components/ThemeToggle";

export function LoginPage({
  userId,
  userToken,
  onUserIdChange,
  onUserTokenChange,
  onSubmit,
  isSubmitting,
  errorMessage,
  theme,
  onToggleTheme,
}) {
  const handleSubmit = (event) => {
    event.preventDefault();
    onSubmit();
  };

  return (
    <main className="login-page">
      <section className="login-card">
        <div className="login-card-header">
          <div>
            <p className="eyebrow">Session gateway</p>
            <h1>Iniciar sesion</h1>
            <p className="login-copy">
              Introduce tus datos para cargar conversaciones y validar tickets. El token
              es opcional mientras la validacion este desactivada.
            </p>
          </div>
          <ThemeToggle theme={theme} onToggle={onToggleTheme} />
        </div>

        {errorMessage ? <div className="inline-alert">{errorMessage}</div> : null}

        <form className="login-form" onSubmit={handleSubmit}>
          <label className="field-label" htmlFor="login-user-id">
            User ID
          </label>
          <input
            id="login-user-id"
            className="text-input"
            value={userId}
            onChange={(event) => onUserIdChange(event.target.value)}
            autoComplete="username"
          />

          <label className="field-label" htmlFor="login-user-token">
            User Token
          </label>
          <input
            id="login-user-token"
            className="text-input"
            type="password"
            value={userToken}
            onChange={(event) => onUserTokenChange(event.target.value)}
            autoComplete="current-password"
            placeholder="Opcional temporalmente"
          />

          <button className="primary-button login-submit" type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Conectando..." : "Entrar"}
          </button>
        </form>
      </section>
    </main>
  );
}
