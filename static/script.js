
const loginTab = document.getElementById("loginTab");
const registerTab = document.getElementById("registerTab");
const switchButton = document.getElementById("switchButton");
const authForm = document.getElementById("authForm");

const nameGroup = document.getElementById("nameGroup");
const phoneGroup = document.getElementById("phoneGroup");
const nameInput = document.getElementById("name");
const phoneInput = document.getElementById("phone");
const passwordInput = document.getElementById("password");

const formTitle = document.getElementById("formTitle");
const formSubtitle = document.getElementById("formSubtitle");
const submitButton = document.getElementById("submitButton");
const switchText = document.getElementById("switchText");
const message = document.getElementById("message");

let currentMode = "login";

function showMessage(text) {
  message.textContent = text;
}

function setMode(mode) {
  currentMode = mode;
  authForm.reset();
  showMessage("");

  const isRegister = mode === "register";

  loginTab.classList.toggle("active", !isRegister);
  registerTab.classList.toggle("active", isRegister);

  nameGroup.classList.toggle("hidden", !isRegister);
  phoneGroup.classList.toggle("hidden", !isRegister);

  nameInput.required = isRegister;
  phoneInput.required = isRegister;

  passwordInput.autocomplete = isRegister
    ? "new-password"
    : "current-password";

  formTitle.textContent = isRegister
    ? "Create your account"
    : "Welcome back!";

  formSubtitle.textContent = isRegister
    ? "Join the TechVerse community."
    : "Login to your student account.";

  submitButton.textContent = isRegister
    ? "Create Account →"
    : "Login to Portal →";

  switchText.firstChild.textContent = isRegister
    ? "Already registered? "
    : "New to TechVerse? ";

  switchButton.textContent = isRegister
    ? "Login here"
    : "Create account";
}

loginTab.addEventListener("click", () => setMode("login"));
registerTab.addEventListener("click", () => setMode("register"));

switchButton.addEventListener("click", () => {
  setMode(currentMode === "login" ? "register" : "login");
});

authForm.addEventListener("submit", (event) => {
  event.preventDefault();

  const email = document.getElementById("email").value.trim();
  const password = passwordInput.value;

  if (!email || !password) {
    showMessage("Please fill in all required fields.");
    return;
  }

  if (password.length < 8) {
    showMessage("Password must be at least 8 characters.");
    return;
  }

  if (currentMode === "register") {
    if (nameInput.value.trim().length < 2) {
      showMessage("Please enter your full name.");
      return;
    }

    if (!/^[0-9]{10}$/.test(phoneInput.value.trim())) {
      showMessage("Enter a valid 10-digit mobile number.");
      return;
    }
  }

  showMessage(
    currentMode === "register"
      ? "Form validated! Backend connection is our next step."
      : "Form validated! Real login will work after backend setup."
  );
});
