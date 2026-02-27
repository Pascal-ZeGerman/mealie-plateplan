export default defineNuxtRouteMiddleware(() => {
  const { loggedIn } = useMealieAuth();
  if (!loggedIn.value) {
    return navigateTo("/login");
  }
});
