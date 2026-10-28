/* Deep-link targets.
   Primary CTAs go to the hosted TokenGuard SaaS.
   Gumroad zip remains a secondary buy path once payout is connected. */
(function () {
  var SAAS_ORIGIN = "https://tokenguard-saas.onrender.com";
  var GUMROAD_URL = "https://labourchef.gumroad.com/l/tokenguard";
  var map = {
    SAAS_URL: SAAS_ORIGIN,
    SAAS_SIGNUP_URL: SAAS_ORIGIN + "/signup",
    SAAS_DEMO_URL: SAAS_ORIGIN + "/app?demo=1",
    GUMROAD_URL: GUMROAD_URL,
    APP_SIGNUP_URL: SAAS_ORIGIN + "/signup",
    APP_SIGNIN_URL: SAAS_ORIGIN + "/signin",
    APP_DEMO_URL: SAAS_ORIGIN + "/app?demo=1",
    APP_DOWNLOAD_URL: SAAS_ORIGIN + "/signup",
    APP_HOME_URL: SAAS_ORIGIN + "/",
  };
  document.querySelectorAll("a").forEach(function (a) {
    var href = a.getAttribute("href") || "";
    if (map[href]) a.setAttribute("href", map[href]);
  });
})();
