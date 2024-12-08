function handleLogin(event) {
  event.preventDefault();
  
  // Reset error messages
  document.querySelectorAll('.error-message').forEach(elem => {
      elem.style.display = 'none';
  });

  // Obtener valores del formulario
  const email = document.getElementById('email').value;
  const password = document.getElementById('password').value;

  // Validación básica
  let isValid = true;

  // Validar correo electrónico
  if (!isValidEmail(email)) {
      showError('emailError', 'Por favor, ingresa un correo válido');
      isValid = false;
  }

  // Validar contraseña
  if (password.length < 6) {
      showError('passwordError', 'La contraseña debe tener al menos 6 caracteres');
      isValid = false;
  }

  if (isValid) {
      // Aquí se puede enviar la solicitud al servidor
      console.log('Intento de inicio de sesión:', { email, password });
      alert('¡Inicio de sesión exitoso! (Esto es solo una demo)');
      
      // Limpiar el formulario
      document.getElementById('loginForm').reset();
  }

  return false;
}

function isValidEmail(email) {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

function showError(elementId, message) {
  const errorElement = document.getElementById(elementId);
  errorElement.textContent = message;
  errorElement.style.display = 'block';
}
