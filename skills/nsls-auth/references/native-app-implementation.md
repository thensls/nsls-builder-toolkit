# Native App Implementation

Reference patterns for React Native, Expo, iOS, and Android apps integrating with NSLS Auth as public OIDC clients.

## Native vs Web — What Changes

| Concern | Web (`application_type: web`) | Native (`application_type: native`) |
|---|---|---|
| Client secret | Required, server-only | Omitted (`token_endpoint_auth_method: none`) |
| Token exchange | Server-side | Inside the app |
| Redirect URI | `https://...` | Custom scheme (`appname://oauth2/callback`), `https://`, or loopback `http://` |
| Token storage | Server (encrypted) | OS secure storage (Keychain / Keystore) |
| PKCE | Required | Required |
| In-app browser | n/a | ASWebAuthenticationSession (iOS) / Custom Tabs (Android), not a webview |

`application_type` is **immutable**. Recreate the client to switch.

## Library Recommendations

| Stack | Library |
|---|---|
| Expo | `expo-auth-session` + `expo-secure-store` |
| Bare React Native | `react-native-app-auth` + `react-native-keychain` |
| iOS Swift | `AppAuth-iOS` |
| Android Kotlin | `AppAuth-Android` |

All four handle PKCE, discovery, and the in-app browser handoff correctly. Don't write the dance by hand.

## Expo + expo-auth-session

```ts
// hooks/useNslsAuth.ts
import * as AuthSession from 'expo-auth-session';
import * as SecureStore from 'expo-secure-store';

const discovery = AuthSession.useAutoDiscovery('https://auth.nsls.org');
const redirectUri = AuthSession.makeRedirectUri({
  scheme: 'thesocietyapp',
  path: 'oauth2/callback',
});

export function useNslsAuth() {
  const [request, response, promptAsync] = AuthSession.useAuthRequest(
    {
      clientId: process.env.EXPO_PUBLIC_OIDC_CLIENT_ID!,
      scopes: ['openid', 'profile', 'email', 'offline_access'],
      redirectUri,
      responseType: 'code',
      usePKCE: true,
    },
    discovery
  );

  return { request, response, promptAsync, discovery, redirectUri };
}
```

Token exchange after `promptAsync()` resolves:

```ts
async function exchangeCode(code: string, codeVerifier: string, discovery: AuthSession.DiscoveryDocument) {
  const tokenResult = await AuthSession.exchangeCodeAsync(
    {
      clientId: process.env.EXPO_PUBLIC_OIDC_CLIENT_ID!,
      code,
      redirectUri,
      extraParams: { code_verifier: codeVerifier },
    },
    discovery
  );

  // tokenResult: { accessToken, idToken, refreshToken, expiresIn, ... }
  // Validate the ID token before trusting it:
  await validateIdToken(tokenResult.idToken!, discovery);

  await SecureStore.setItemAsync('nsls_refresh_token', tokenResult.refreshToken!);
  return tokenResult;
}
```

`expo-auth-session` does NOT validate the ID token signature for you. You must validate `iss`, `aud`, `nonce`, `exp`, and the signature against JWKS yourself, or use a JWT library like `jose`.

## Bare React Native + react-native-app-auth

```ts
import { authorize, refresh, logout } from 'react-native-app-auth';
import * as Keychain from 'react-native-keychain';

const config = {
  issuer: 'https://auth.nsls.org',
  clientId: 'thesociety-mobile',
  redirectUrl: 'thesocietyapp://oauth2/callback',
  scopes: ['openid', 'profile', 'email', 'offline_access'],
  // PKCE is on by default
};

export async function signIn() {
  const result = await authorize(config);
  await Keychain.setGenericPassword('nsls_refresh', result.refreshToken, {
    service: 'nsls.auth.refresh',
    accessible: Keychain.ACCESSIBLE.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
  });
  return result;
}

export async function refreshTokens(refreshToken: string) {
  return refresh(config, { refreshToken });
}

export async function signOut(idToken: string) {
  return logout(config, {
    idToken,
    postLogoutRedirectUrl: 'thesocietyapp://oauth2/logout',
  });
}
```

`react-native-app-auth` uses the platform's AppAuth SDK underneath, which does validate ID tokens.

## ID Token Validation (Expo / Manual)

When the library doesn't validate for you:

```ts
import { jwtVerify, createRemoteJWKSet, decodeJwt } from 'jose';

async function validateIdToken(idToken: string, discovery: { jwks_uri: string; issuer: string }) {
  const JWKS = createRemoteJWKSet(new URL(discovery.jwks_uri));
  const { payload } = await jwtVerify(idToken, JWKS, {
    issuer: discovery.issuer,
    audience: process.env.EXPO_PUBLIC_OIDC_CLIENT_ID,
  });
  // Also verify nonce matches the one stored before the authorize call.
  if (payload.nonce !== expectedNonce) {
    throw new Error('Nonce mismatch');
  }
  return payload;
}
```

## Custom URI Scheme Setup

### iOS (Info.plist)

```xml
<key>CFBundleURLTypes</key>
<array>
  <dict>
    <key>CFBundleURLSchemes</key>
    <array>
      <string>thesocietyapp</string>
    </array>
  </dict>
</array>
```

### Android (AndroidManifest.xml)

```xml
<activity android:name=".MainActivity" ...>
  <intent-filter android:autoVerify="false">
    <action android:name="android.intent.action.VIEW" />
    <category android:name="android.intent.category.DEFAULT" />
    <category android:name="android.intent.category.BROWSABLE" />
    <data android:scheme="thesocietyapp" android:host="oauth2" />
  </intent-filter>
</activity>
```

## Token Storage Rules

- **Refresh tokens** → OS secure storage (`expo-secure-store` / Keychain / Keystore). Never `AsyncStorage`. Never plain files.
- **Access tokens** → in-memory for the app session. Don't persist them; refresh as needed.
- **ID tokens** → in-memory for the app session. Use the claims, then drop the token.

## Logout

Native logout has the same shape as web:

1. Clear local app session (in-memory + remove refresh token from Keychain).
2. Optionally redirect through `/oidc/logout` with `id_token_hint` and a registered `post_logout_redirect_uri` like `thesocietyapp://oauth2/logout`.
3. The browser-style end-session redirect lands the user on the app's logout-handler URL, which closes the auth view.

## Refresh Loop

```ts
async function getValidAccessToken(): Promise<string> {
  if (accessTokenStillValid()) return cachedAccessToken;

  const refreshToken = await readRefreshTokenFromSecureStore();
  if (!refreshToken) {
    throw new Error('No refresh token; force re-login');
  }

  try {
    const result = await refresh(config, { refreshToken });
    cachedAccessToken = result.accessToken;
    if (result.refreshToken) {
      await writeRefreshTokenToSecureStore(result.refreshToken);
    }
    return result.accessToken;
  } catch (err) {
    // invalid_grant — central session was revoked
    await deleteRefreshToken();
    throw err; // app should clear session and force re-login
  }
}
```

## Common Native-Specific Gotchas

1. **Webview is not allowed.** Use ASWebAuthenticationSession on iOS or Custom Tabs on Android. Embedded webviews break SSO and may be rejected by Apple review.
2. **AsyncStorage is not secure storage.** Refresh tokens belong in Keychain / Keystore.
3. **Custom scheme registration is per-platform.** Both iOS Info.plist and Android manifest must declare the scheme, or the redirect silently fails on one platform.
4. **`application_type: native` is immutable.** Switching from `web` requires deleting and recreating the client.
5. **Browser-reserved schemes are rejected.** `javascript:`, `data:`, etc. won't pass NSLS Auth's redirect URI validation.
6. **Loopback `http://` only for local dev.** Production must use a custom scheme or `https://` universal link.
