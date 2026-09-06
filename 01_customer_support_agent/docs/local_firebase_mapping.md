Run from the project directory in the PowerShell session containing the verified
Firebase UID and ID token. Replace only the variable names `$verifiedUid` and
`$idToken` below with your existing session variable names; never paste their
literal values into a command or chat. The helper re-verifies the token and checks
that its UID matches before writing. If the token has expired, repeat your existing
sign-in procedure locally first.

```powershell
@{uid=$verifiedUid; token=$idToken} | ConvertTo-Json -Compress | .\.venv\Scripts\python.exe -m scripts.provision_local_firebase
```

Values travel through stdin, not command arguments, files, or printed output.
The token is held only in process memory during verification. The UID is stored
only as the local customer's Firebase auth_subject. Email and display_name are
left null on new rows. Existing mappings are reused without updates; disabled or
pending accounts fail and are never reactivated. Demo customers and orders are
never updated. A failed verification rolls back a newly inserted row.

Requires APP_ENV=development and a loopback PostgreSQL DATABASE_URL without query
overrides. Confirm that this configured database is your local development
database (not a tunnel to a remote database) before running. There is no route or
normal-authentication auto-provisioning change. No migration is needed.

Success prints only LOCAL_FIREBASE_MAPPING=PASS IDENTITY_RESOLUTION=PASS
TOKEN_STORED=NO. Share only that status line if confirmation is needed.
