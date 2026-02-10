import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import * as fs from 'fs';
import * as path from 'path';

// This runs in Node.js - Don't use client-side code here (browser APIs, JSX...)

const isProd = process.env.NODE_ENV === 'production';

// Load versions from versions.json
const versionsPath = path.join(__dirname, 'versions.json');
const versions: string[] = fs.existsSync(versionsPath)
  ? JSON.parse(fs.readFileSync(versionsPath, 'utf-8'))
  : [];

// Build versions config dynamically
const versionsConfig: Record<string, {label: string; banner: 'unreleased' | 'none'}> = {
  current: {
    label: 'Next',
    banner: 'unreleased',
  },
};

// Add all released versions
versions.forEach((version) => {
  versionsConfig[version] = {
    label: version,
    banner: 'none',
  };
});

// Latest stable version (first in versions.json)
const latestVersion = versions[0] || 'current';

const config: Config = {
  title: 'UGAS',
  tagline:
    'An open, engine-agnostic specification for standardizing gameplay logic across game engines and AI world models.',
  favicon: 'img/favicon.ico',

  // Future flags, see https://docusaurus.io/docs/api/docusaurus-config#future
  future: {
    v4: true, // Improve compatibility with the upcoming Docusaurus v4
  },

  // Set the production url of your site here
  url: 'https://ugas.jbltx.com',
  // Set the /<baseUrl>/ pathname under which your site is served
  // For GitHub pages deployment, it is often '/<projectName>/'
  baseUrl: '/',

  // GitHub pages deployment config.
  // If you aren't using GitHub pages, you don't need these.
  organizationName: 'jbltx', // Usually your GitHub org/user name.
  projectName: 'ugas', // Usually your repo name.

  onBrokenLinks: 'throw',

  // Even if you don't use internationalization, you can use this field to set
  // useful metadata like html lang. For example, if your site is Chinese, you
  // may want to replace "en" with "zh-Hans".
  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.ts',
          remarkPlugins: [remarkMath],
          rehypePlugins: [rehypeKatex],
          includeCurrentVersion: !isProd,
          onlyIncludeVersions: isProd ? versions : undefined,
          lastVersion: 'current',
          versions: versionsConfig,
          // Please change this to your repo.
          // Remove this to remove the "edit this page" links.
          editUrl:
            'https://github.com/facebook/docusaurus/tree/main/packages/create-docusaurus/templates/shared/',
        },
        blog: false,
        // blog: {
        //   showReadingTime: true,
        //   feedOptions: {
        //     type: ['rss', 'atom'],
        //     xslt: true,
        //   },
        //   // Please change this to your repo.
        //   // Remove this to remove the "edit this page" links.
        //   editUrl:
        //     'https://github.com/facebook/docusaurus/tree/main/packages/create-docusaurus/templates/shared/',
        //   // Useful options to enforce blogging best practices
        //   onInlineTags: 'warn',
        //   onInlineAuthors: 'warn',
        //   onUntruncatedBlogPosts: 'warn',
        // },
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],
  plugins: [
    [
      require.resolve('@cmfcmf/docusaurus-search-local'),
      {
        indexDocs: true,
        indexBlog: false,
        indexPages: false,
      },
    ],
  ],

  themeConfig: {
    // Replace with your project's social card
    image: 'img/docusaurus-social-card.jpg',
    colorMode: {
      respectPrefersColorScheme: true,
    },
    metadata: [
      {
        name: 'description',
        content:
          'An open, engine-agnostic specification for standardizing gameplay logic across game engines and AI world models.',
      },
      {
        name: 'keywords',
        content:
          'UGAS, gameplay ability system, gameplay effects, gameplay attributes, gameplay tags, specification',
      },
      {
        property: 'og:title',
        content: 'Universal Gameplay Ability System (UGAS)',
      },
      {
        property: 'og:description',
        content:
          'An open, engine-agnostic specification for standardizing gameplay logic across game engines and AI world models.',
      },
      {
        property: 'og:type',
        content: 'website',
      },
      {
        name: 'twitter:card',
        content: 'summary_large_image',
      },
      {
        name: 'twitter:title',
        content: 'Universal Gameplay Ability System (UGAS)',
      },
      {
        name: 'twitter:description',
        content:
          'An open, engine-agnostic specification for standardizing gameplay logic across game engines and AI world models.',
      },
    ],
    navbar: {
      title: 'UGAS',
      logo: {
        alt: 'UGAS Logo',
        src: 'img/logo-black.svg',
        srcDark: 'img/logo.svg',
      },
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'specSidebar',
          position: 'left',
          label: 'Specification',
        },
        {
          type: 'docsVersionDropdown',
          position: 'right',
        },
        // {to: '/blog', label: 'Blog', position: 'left'},
        {
          href: 'https://github.com/jbltx/ugas',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
    prism: {
      theme: prismThemes.vsLight,
      darkTheme: prismThemes.vsDark,
    },
  } satisfies Preset.ThemeConfig,
  stylesheets: [
    {
      href: 'https://cdn.jsdelivr.net/npm/katex@0.16.28/dist/katex.min.css',
      type: 'text/css',
      integrity:
        'sha384-+W9OcrYK2/bD7BmUAk+xeFAyKp0QjyRQUCxeU31dfyTt/FrPsUgaBTLLkVf33qWt',
      crossorigin: 'anonymous',
    }
  ],
};

export default config;
