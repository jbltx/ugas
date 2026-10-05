# Releasing

A release is cut the way it always has been: merge the changesets Release PR, then publish a
GitHub release whose tag is the new version (e.g. `1.0.0-draft.8`). Publishing the release
runs two workflows:

- [`publish-docs.yml`](.github/workflows/publish-docs.yml) builds the version tree for
  ugas.jbltx.com and opens the docs PR.
- [`publish-npm.yml`](.github/workflows/publish-npm.yml) builds [`packages/spec`](packages/spec)
  from the same sources and publishes it to npm at that version. A prerelease version
  (anything with a `-`, like every draft) goes to the `next` dist-tag; a final version goes
  to `latest`. It authenticates with npm trusted publishing (OIDC), so there is no npm
  token secret, and npm attaches a provenance statement.

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

## One-time npm setup (owner)

Trusted publishing is configured per package on npmjs.com, and npm only lets you do that
once the package exists. So the first version has to be published by hand:

1. Sign in to npmjs.com (2FA on) and create the npm organization `ugas` (free, public
   packages only). The scope `@ugas` has to belong to you before `@ugas/spec` can be
   published.
2. Build locally as above, then publish from the build directory:
   `cd packages/spec/build && npm publish --access public --tag next`.
   (No provenance on this one; it can only be generated in CI.)
3. On npmjs.com, open the package, then **Settings → Trusted publishing → GitHub Actions**
   and enter:
   - Organization or user: `jbltx`
   - Repository: `ugas`
   - Workflow filename: `publish-npm.yml`
   - Environment: leave empty
4. Optional but recommended: in the same settings, set **Publishing access** to require
   2FA and disallow tokens, so only the workflow can publish.

From then on every published GitHub release publishes the package. If a release's npm
publish fails, fix the cause and re-run the workflow run; it skips a version that is
already on npm.
