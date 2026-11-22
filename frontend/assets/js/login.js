import { setupAuth, onAuthStateChanged, signInWithEmailAndPassword, createUserWithEmailAndPassword, sendPasswordResetEmail, GoogleAuthProvider, signInWithPopup } from './auth-client.js';
const $ = id => document.getElementById(id);
let registering = false;
$('switch-mode').onclick = () => {
  registering = !registering;
  $('confirm-label').hidden = !registering;
  $('confirm-password').required = registering;
  $('reset-password').hidden = registering;
  $('password').autocomplete = registering ? 'new-password' : 'current-password';
  $('submit').textContent = registering ? 'Create account' : 'Sign in';
  $('auth-title').textContent = registering ? 'Create your account' : 'Welcome back';
  $('switch-label').textContent = registering ? 'Already have an account?' : 'New to URUS?';
  $('switch-mode').textContent = registering ? 'Sign in' : 'Create an account';
  $('intro').textContent = registering ? 'Create your URUS account.' : 'Sign in to manage your inventory.';
  $('message').textContent = '';
};
try {
  const auth = await setupAuth();
  $('google-sign-in').onclick = async () => {
    $('message').textContent = ''; $('google-sign-in').disabled = true;
    try { await signInWithPopup(auth, new GoogleAuthProvider()); }
    catch (error) {
      if (error.code === 'auth/popup-closed-by-user') $('message').textContent = 'Sign-in was cancelled.';
      else if (error.code === 'auth/account-exists-with-different-credential') $('message').textContent = 'An account with this email uses a different sign-in method. Please sign in with that method.';
      else $('message').textContent = error.message;
    } finally { $('google-sign-in').disabled = false; }
  };
  $('reset-password').onclick = async () => {
    const email = $('email').value.trim();
    if (!email || !$('email').checkValidity()) { $('message').textContent = 'Enter your email address first.'; $('email').focus(); return; }
    $('reset-password').disabled = true;
    try { await sendPasswordResetEmail(auth, email); $('message').textContent = 'If an account exists for this email, a password reset message has been sent.'; }
    catch (error) { $('message').textContent = error.code === 'auth/invalid-email' ? 'Please enter a valid email address.' : 'Could not send the reset email. Please try again later.'; }
    finally { $('reset-password').disabled = false; }
  };
  onAuthStateChanged(auth, async user => {
    if (!user) return;
    try {
      const response = await fetch('/api/v1/me', {headers:{Authorization:`Bearer ${await user.getIdToken()}`}});
      const data = (response.headers.get('content-type') || '').includes('application/json') ? await response.json() : null;
      if (!response.ok || !data) throw new Error(data?.error || `Unable to load your account (${response.status}). Please reload the page.`);
      location.replace(data.businesses.length ? '/dashboard.html' : '/onboarding.html');
    } catch (error) { $('message').textContent = error.message; $('submit').disabled = false; }
  });
  $('login-form').addEventListener('submit', async event => {
    event.preventDefault(); $('message').textContent = '';
    const email = $('email').value.trim(), password = $('password').value;
    if (registering && password !== $('confirm-password').value) { $('message').textContent = 'Passwords do not match.'; return; }
    $('submit').disabled = true;
    try { if (registering) await createUserWithEmailAndPassword(auth,email,password); else await signInWithEmailAndPassword(auth,email,password); }
    catch (error) { $('message').textContent = error.code === 'auth/invalid-credential' ? 'Email or password could not be verified. Check them and try again, or reset your password.' : error.message; $('submit').disabled = false; }
  });
} catch (error) { $('message').textContent = error.message; }
