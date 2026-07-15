import { BookOpen, Loader2 } from "lucide-react";
import type { FormEvent } from "react";

import type { AuthMode } from "../hooks/useAuth";

type LoginPageProps = {
  authError: string | null;
  authMode: AuthMode;
  authPassword: string;
  authUsername: string;
  isSubmitting: boolean;
  onModeChange: (mode: AuthMode) => void;
  onPasswordChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onUsernameChange: (value: string) => void;
};

export function AuthLoadingPage() {
  return (
    <main className="login-shell" data-testid="auth-loading">
      <section className="login-card">
        <Loader2 className="spin" size={22} />
        <p>正在确认登录状态</p>
      </section>
    </main>
  );
}

export function LoginPage(props: LoginPageProps) {
  const {
    authError,
    authMode,
    authPassword,
    authUsername,
    isSubmitting,
    onModeChange,
    onPasswordChange,
    onSubmit,
    onUsernameChange
  } = props;
  return (
    <main className="login-shell" data-testid="login-page">
      <section className="login-card">
        <div className="login-brand">
          <BookOpen size={28} />
          <div>
            <p className="eyebrow">Listen Book</p>
            <h1>{authMode === "login" ? "登录账号" : "创建账号"}</h1>
          </div>
        </div>
        <form className="auth-form" noValidate onSubmit={onSubmit}>
          <div className="auth-tabs">
            <button
              className={authMode === "login" ? "active" : ""}
              data-testid="auth-login-tab"
              onClick={() => onModeChange("login")}
              type="button"
            >
              登录
            </button>
            <button
              className={authMode === "register" ? "active" : ""}
              data-testid="auth-register-tab"
              onClick={() => onModeChange("register")}
              type="button"
            >
              注册
            </button>
          </div>
          <input
            autoComplete="username"
            data-testid="auth-username"
            onChange={(event) => onUsernameChange(event.target.value)}
            placeholder="用户名"
            required
            type="text"
            value={authUsername}
          />
          <input
            autoComplete={authMode === "login" ? "current-password" : "new-password"}
            data-testid="auth-password"
            minLength={6}
            onChange={(event) => onPasswordChange(event.target.value)}
            placeholder="密码"
            required
            type="password"
            value={authPassword}
          />
          {authError ? <p className="auth-error">{authError}</p> : null}
          <button data-testid="auth-submit" disabled={isSubmitting} type="submit">
            {isSubmitting ? <Loader2 className="spin" size={14} /> : null}
            {authMode === "login" ? "登录账号" : "创建账号"}
          </button>
        </form>
      </section>
    </main>
  );
}
