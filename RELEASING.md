# Releasing

A release is cut the way it always has been: merge the changesets Release PR, then publish a
GitHub release whose tag is the new version (e.g. `1.0.0-draft.8`). Publishing the release
runs two workflows:

- [`publish-docs.yml`](.github/workflows/publish-docs.yml) builds the version tree for
  ugas.jbltx.com and opens the docs PR.
- [`publish-npm.yml`](.github/workflows/publish-npm.yml) builds [`packages/spec`](packages/spec)
  from the same sources and **stages** it on npm at that version. A prerelease version
  (anything with a `-`, like every draft) is staged for the `next` dist-tag; a final version
  for `latest`. It authenticates with npm trusted publishing (OIDC), so there is no npm
  token secret, and npm attaches a provenance statement.

A staged version is not installable until the owner approves it (see below). The trusted
publisher only allows `npm stage publish`, so the workflow cannot publish directly or move
dist-tags.

The npm version is not stored anywhere new: the build reads the root `package.json`
version, and the workflow fails if the release tag disagrees with it.

## Building the package locally

Needs Node 20.10+, Python 3 with PyYAML, `asciidoctor` and `pandoc`.

```sh
cd packages/spec
npm ci
npm run build       # assembles packages/spec/build/, the directory that gets published
npm test
npm run pack:dry    # lists the tarball
```

## Approving a staged version (owner)

The workflow run's summary links the package once the version is staged. Approval needs
your 2FA; a CI token cannot approve.

1. Open https://www.npmjs.com/package/@ugas/spec, signed in.
2. Open the **Staged Packages** tab, check the version, dist-tag and contents.
3. Click **Approve** and confirm with 2FA. The version goes live under the dist-tag it was
   staged with.

From a terminal instead (npm 11.15.0 or later): `npm stage list @ugas/spec`, optionally
`npm stage download <stage-id>` to inspect the tarball, then `npm stage approve <stage-id>`.
`npm stage reject <stage-id>` drops a bad one.

The dist-tag is fixed when the version is staged. Any later change, such as pointing
`latest` elsewhere, is yours to do by hand: `npm dist-tag add @ugas/spec@<version> <tag>`.

If a release's staging fails, fix the cause and re-run the workflow run. It skips a version
that is already on npm or already staged.

## One-time npm setup (owner)

Trusted publishing is configured per package on npmjs.com, and npm only lets you do that
once the package exists. So the first version has to be published by hand:

1. Sign in to npmjs.com (2FA on) and create the npm organization `ugas` (free, public
   packages only). The scope `@ugas` has to belong to you before `@ugas/spec` can be
   published.
2. Build locally as above, then publish from the build directory:
   `cd packages/spec/build && npm publish --access public --tag next --provenance=false`.
   (No provenance on this one; it can only be generated in CI.)
3. On npmjs.com, open the package, then **Settings → Trusted publishing → GitHub Actions**
   and enter:
   - Organization or user: `jbltx`
   - Repository: `ugas`
   - Workflow filename: `publish-npm.yml`
   - Environment: leave empty
   - Allowed actions: staged publishing only. Leave both the `npm publish` and the
     `npm dist-tag` boxes unchecked.
4. In the same settings, set **Publishing access** to **Require two-factor authentication
   and disallow tokens**. The workflow keeps working: npm documents that this setting only
   blocks traditional tokens, and trusted publishers authenticate with OIDC
   ([trusted publishers](https://docs.npmjs.com/trusted-publishers/)). Approving a staged
   version still asks for your 2FA ([staged publishing](https://docs.npmjs.com/staged-publishing/)).
