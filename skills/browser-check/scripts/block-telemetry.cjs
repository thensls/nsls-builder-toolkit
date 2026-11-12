// block-telemetry.cjs — preloaded into every Node process Expect starts
// (NODE_OPTIONS=--require), so its vendor telemetry can't leave the machine.
//
// Why: expect-cli 0.1.3 honours NO_TELEMETRY=1 for its PostHog analytics, but
// its OpenTelemetry traces go to Axiom unconditionally (measured 2026-11-12:
// ~175 connection samples to api.axiom.co in one run with NO_TELEMETRY=1 set).
// It also phones expect.dev for a version check. This refuses all three at
// DNS and socket level. Nothing else is touched: Claude, npm and the page
// under test connect normally.
"use strict";
const dns = require("node:dns");
const net = require("node:net");
const tls = require("node:tls");

const BLOCKED = [/(^|\.)posthog\.com$/i, /(^|\.)axiom\.co$/i, /(^|\.)expect\.dev$/i];
const isBlocked = (host) => typeof host === "string" && BLOCKED.some((re) => re.test(host.replace(/\.$/, "")));
const refusal = (host) => Object.assign(new Error(`browser-check: blocked vendor telemetry host ${host}`), { code: "ENOTFOUND" });

if (process.env.BROWSER_CHECK_BLOCK_LOG) {
  // Prove the preload reached this process (used by the self-test).
  require("node:fs").appendFileSync(process.env.BROWSER_CHECK_BLOCK_LOG, `loaded pid=${process.pid}\n`);
}
const note = (host) => {
  if (process.env.BROWSER_CHECK_BLOCK_LOG) {
    require("node:fs").appendFileSync(process.env.BROWSER_CHECK_BLOCK_LOG, `blocked ${host} pid=${process.pid}\n`);
  }
};

// DNS: callback and promise forms.
const origLookup = dns.lookup;
dns.lookup = function (host, ...rest) {
  if (isBlocked(host)) {
    note(host);
    const cb = rest[rest.length - 1];
    if (typeof cb === "function") return process.nextTick(cb, refusal(host));
  }
  return origLookup.call(this, host, ...rest);
};
if (dns.promises) {
  const origP = dns.promises.lookup;
  dns.promises.lookup = function (host, ...rest) {
    if (isBlocked(host)) { note(host); return Promise.reject(refusal(host)); }
    return origP.call(this, host, ...rest);
  };
}

// Sockets: catch anything that resolves on its own or passes servername.
function guard(orig) {
  return function (...args) {
    const o = args[0] && typeof args[0] === "object" ? args[0] : { host: args[1] };
    const host = o.servername || o.host || o.hostname;
    if (isBlocked(host)) { note(host); throw refusal(host); }
    return orig.apply(this, args);
  };
}
tls.connect = guard(tls.connect);
net.connect = guard(net.connect);
net.createConnection = guard(net.createConnection);
