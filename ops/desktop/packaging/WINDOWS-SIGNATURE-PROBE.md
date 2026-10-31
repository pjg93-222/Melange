# Windows updater verification without PowerShell

The updater previously launched PowerShell for Get-AuthenticodeSignature and installer progress inspection. A corporate policy that permits the application but blocks its PowerShell child would prevent updates. Both live operations now use a fixed native probe through the bundled Python runtime. The existing signed manifest, package hashes before and after inspection, publisher pin, rollback and sequence protections remain in force.

## Trust policy

WinVerifyTrust returns a LONG: only exact zero is Windows trust success. The probe preserves Windows' standard timestamp policy and does not use WTD_LIFETIME_SIGNING_FLAG or reject a correctly timestamped signature merely because its signer expired today. Exact zero still requires the application's pinned signer and the signed manifest's publisher allow-list. Auxiliary offline chain diagnostics do not override Windows' successful verdict.

For a nonzero result, the only permitted application policy exception is CERT_E_UNTRUSTEDROOT for the exact pinned self-signed certificate, with no additional provider, signer, counter-signer or chain errors and valid certificate time at the provider's verified timestamp. Unsigned, bad digest, expired, revoked, unknown and other nonzero results are refused. The exception is our explicit publisher policy, not a claim that Windows returned success. Verification uses cached revocation information without network retrieval. A missing verifier/verdict remains distinguishable from a valid refusal.

The probe loads wintrust/crypt32/kernel32/shell32 from System32, holds the inspected file read-only with write/delete sharing refused, and always closes WinTrust state after verification. No certificate store is modified.

Primary API references:

- https://learn.microsoft.com/en-us/windows/win32/api/wintrust/nf-wintrust-winverifytrust
- https://learn.microsoft.com/en-us/windows/win32/api/wintrust/ns-wintrust-wintrust_data
- https://learn.microsoft.com/en-us/windows/win32/api/wintrust/ns-wintrust-crypt_provider_sgnr
- https://learn.microsoft.com/en-us/windows/win32/api/wintrust/ns-wintrust-crypt_provider_cert
- https://learn.microsoft.com/en-us/windows/win32/api/wincrypt/ns-wincrypt-cert_chain_context
- https://learn.microsoft.com/en-us/windows/win32/api/wincrypt/nf-wincrypt-certverifytimevalidity

## Authenticated probe closure

The executable is resolved internally from the selected app's installed runtime. The fixed invocation uses `-I -S -B -u` and accepts only the signature or installer-process observation mode. No command, WQL, script path or interpreter is accepted from application settings or JSON input.

`signature-probe-runtime.json`, shipped inside the integrity-protected ASAR, pins the reviewed interpreter/stdlib/DLL/bytecode closure for each app. Site packages are excluded because isolated/no-site mode cannot import them. Unexpected files, directories, `_pth`, `pyvenv.cfg`, reparse points and changed bytes are refused. Windows case-only spelling differences remain valid. The native script itself is pinned by the existing compiled application inventory. Normal backend commands already use `-B`; inherited child environments now also disable bytecode writes and remove venv-launcher injection.

The reviewed baseline closures are Mentat 707 files/34,012,647 bytes, Terrier 705 files/33,490,606 bytes and Melange 739 files/35,067,839 bytes. They differ and must not be substituted for one another.

Normal Windows builder `beforePack` verifies the selected runtime against this authority before signing. The custom release orchestration must run the same check on its staged runtime and actual ASAR authority before signing. Use `refresh_signature_probe_runtime.py --app APP --python-root PATH` to check; `--write` explicitly changes the reviewed ASAR authority and requires source review. Never silently regenerate it from an unreviewed candidate.

## Installer observation

The native observer enumerates process IDs with Toolhelp and uses limited query rights to match the exact installer image. Only then does the authenticated CPython `_wmi` extension read command-line and creation-time fields for that OS-observed numeric PID using a fixed query template. The random activation token must be an exact Windows argv element; creation time must match the held process handle. Only matched PID/time/path are returned. No unrelated command lines leave the probe. The existing receipt, PID reuse, unknown and abandoned-state rules remain unchanged. WMI failure grants nothing.

## Validation scope

Focused tests cover real pinned signature, unsigned and tampered PE bytes, a disposable untrusted self-signed fixture without trust-store changes, wrong publisher, missing verdict, and an actual timestamped vendor certificate that expired in April 2025 but remains valid under Windows' timestamp policy. Test-only matching-pin overrides never alter the shipped publisher pin.

The actual 484,129,136-byte held Mentat installer returned WinTrust zero and the correct pin in 2.834 seconds on this PC. The authenticated isolated probe test covers actual native process observation, wrong token, interpreter/script/bytecode/config tampering, case-only paths and no bytecode writes. These are local tests, not proof that a corporate ThreatLocker policy permits the bundled interpreter or that a physical work-PC update has completed.

Focused validation commands (explicit fixture/dependency locations are supplied by the operator; tests have no developer-machine defaults):

```text
python -B -m unittest discover -s ops/desktop/packaging -p test_native_windows_signature.py -v
node --test ops/desktop/client/tests/native-signature.test.cjs ops/desktop/client/tests/publisher-thumbprint.test.cjs ops/desktop/client/tests/installer-activation.test.cjs ops/desktop/client/tests/build-native.test.cjs ops/desktop/client/tests/runtime-configuration.test.cjs
node --test ops/desktop/client/tests/signature-probe-runtime.test.cjs
node --test ops/desktop/client/tests/builder-update-source.test.cjs ops/desktop/client/tests/backend-command.test.cjs
node --test ops/desktop/client/tests/release-files.test.cjs
python -B ops/desktop/packaging/refresh_module_inventory.py --bootstrap-only
```

Native tests require `SIGNATURE_TEST_SIGNED_PE`, `SIGNATURE_TEST_SIGNTOOL` and `SIGNATURE_TEST_TIMESTAMPED_PE`; authenticated probe tests require `SIGNATURE_TEST_PYTHON_ROOT` and `SIGNATURE_TEST_SIGNED_PE`. The first native run passed 7 tests, the main JS group 38, authenticated probe 2, builder/backend 5 and ASAR closure 2. The ASAR test initially lacked its development dependency and passed after setting the existing appropriate `NODE_PATH`; this was not an application failure. All three explicit baseline roster checks also passed. The source-only sleep/dead-child regression added by the parallel release reviewer remains in the parent commit.
