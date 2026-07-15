import type { FormEvent } from "react";
import { useRef, useState } from "react";

import { fetchCurrentUser, loginUser, logoutUser, registerUser } from "../api";
import type { User } from "../types";

export type AuthMode = "login" | "register";

export function useAuth() {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);
  const [authMode, setAuthMode] = useState<AuthMode>("login");
  const [authUsername, setAuthUsername] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authError, setAuthError] = useState<string | null>(null);
  const [isAuthSubmitting, setIsAuthSubmitting] = useState(false);
  const isAuthSubmittingRef = useRef(false);

  async function bootstrap() {
    setIsCheckingAuth(true);
    try {
      const user = await fetchCurrentUser();
      setCurrentUser(user);
      return user;
    } catch {
      setCurrentUser(null);
      return null;
    } finally {
      setIsCheckingAuth(false);
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isAuthSubmittingRef.current) {
      return null;
    }

    const username = authUsername.trim();
    const validationError = validateAuthForm(authMode, username, authPassword);
    if (validationError) {
      setAuthError(validationError);
      return null;
    }

    isAuthSubmittingRef.current = true;
    setAuthError(null);
    setIsAuthSubmitting(true);
    try {
      const response =
        authMode === "login"
          ? await loginUser(username, authPassword)
          : await registerUser(username, authPassword);
      setCurrentUser(response.user);
      setAuthPassword("");
      setAuthMode("login");
      return response.user;
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "账号操作失败");
      return null;
    } finally {
      isAuthSubmittingRef.current = false;
      setIsAuthSubmitting(false);
    }
  }

  async function logout() {
    await logoutUser().catch(() => {
      // Local logout should still clear the UI if the server request fails.
    });
    setAuthError(null);
    setAuthMode("login");
    setCurrentUser(null);
  }

  return {
    authError,
    authMode,
    authPassword,
    authUsername,
    bootstrap,
    currentUser,
    isAuthSubmitting,
    isCheckingAuth,
    logout,
    setAuthMode,
    setAuthPassword,
    setAuthUsername,
    submit
  };
}

function validateAuthForm(mode: AuthMode, username: string, password: string) {
  if (!username) {
    return "请输入用户名";
  }
  if (!password) {
    return "请输入密码";
  }
  if (mode === "register" && username.length < 3) {
    return "用户名至少需要 3 个字符";
  }
  if (mode === "register" && password.length < 6) {
    return "密码至少需要 6 个字符";
  }
  return null;
}
