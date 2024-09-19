const hamBurger = document.querySelector(".toggle-btn");

hamBurger.addEventListener("click", function () {
  document.querySelector("#sidebar").classList.toggle("expand");
});

// Función para cerrar sesión
function cerrarSesion() {
  // Redireccionar a la ruta de cierre de sesión
  window.location.href = "/logout";
  
}