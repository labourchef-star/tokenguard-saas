/* Deep-link targets.
   Primary CTAs on the phone landing go to Gumroad (GUMROAD_URL).
   Local app demos remain secondary via APP_* placeholders. */
(function () {
  var GUMROAD_URL = "https://labourchef.gumroad.com/l/tokenguard";
  var APP_ORIGIN = localStorage.getItem("tokenguard_app_origin")
    || localStorage.getItem("loop_stop_app_origin")
    || "http://127.0.0.1:8788";
  var map = {
    GUMROAD_URL: GUMROAD_URL,
    APP_SIGNUP_URL: APP_ORIGIN + "/signup",
    APP_SIGNIN_URL: APP_ORIGIN + "/signin",
    APP_DEMO_URL: APP_ORIGIN + "/app?demo=1",
    APP_DOWNLOAD_URL: APP_ORIGIN + "/download",
    APP_HOME_URL: APP_ORIGIN + "/",
  };
  document.querySelectorAll("a").forEach(function (a) {
    var href = a.getAttribute("href") || "";
    if (map[href]) a.setAttribute("href", map[href]);
  });
})();
