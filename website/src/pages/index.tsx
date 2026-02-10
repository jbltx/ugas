import type {ReactNode} from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';

import styles from './index.module.css';

function HomepageHeader() {
  const {siteConfig} = useDocusaurusContext();
  return (
    <header className={clsx('hero', styles.heroBanner)}>
      <div className={clsx('container', styles.heroGrid)}>
        <div className={styles.heroContent}>
          <span className={styles.eyebrow}>Specification v1.0</span>
          <div className={styles.titleRow}>
            <img
              src="/img/logo-black.svg"
              alt=""
              className={clsx(styles.heroLogo, styles.logoLight)}
              aria-hidden="true"
            />
            <img
              src="/img/logo.svg"
              alt=""
              className={clsx(styles.heroLogo, styles.logoDark)}
              aria-hidden="true"
            />
            <Heading as="h1" className={styles.heroTitle}>
              {siteConfig.title}
            </Heading>
          </div>
          <p className={styles.heroTagline}>Universal Gameplay Ability System</p>
          <p className={styles.heroSubtitle}>{siteConfig.tagline}</p>
          <div className={styles.buttons}>
            <Link className="button button--primary button--lg" to="/docs/spec">
              Read the spec
            </Link>
            {/* <Link className="button button--secondary button--lg" to="/docs/intro">
              Quick start
            </Link> */}
          </div>
          <div className={styles.heroMeta}>
            <span>Engine-agnostic</span>
            <span>Deterministic</span>
            <span>Network-ready</span>
          </div>
        </div>
        <div className={styles.heroPanel}>
          <div className={styles.panelCard}>
            <div className={styles.panelHeader}>Gameplay Controller</div>
            <div className={styles.panelGrid}>
              <div>
                <span className={styles.panelLabel}>Attributes</span>
                <div className={styles.panelPills}>
                  <span className={styles.panelPill}>Health</span>
                  <span className={styles.panelPill}>Mana</span>
                  <span className={styles.panelPill}>Stamina</span>
                  <span className={styles.panelPill}>Armor</span>
                </div>
              </div>
              <div>
                <span className={styles.panelLabel}>Tags</span>
                <div className={styles.panelPills}>
                  <span className={styles.panelPill}>State.Debuff.Stunned.Magic</span>
                </div>
              </div>
              <div>
                <span className={styles.panelLabel}>Abilities</span>
                <div className={styles.panelPills}>
                  <span className={styles.panelPill}>Grant</span>
                  <span className={styles.arrowRight}></span>
                  <span className={styles.panelPill}>TryActivate</span>
                  <span className={styles.arrowRight}></span>
                  <span className={styles.panelPill}>Commit</span>
                  <span className={styles.arrowRight}></span>
                  <span className={styles.panelPill}>Execute</span>
                </div>
              </div>
              <div>
                <span className={styles.panelLabel}>Effects</span>
                <div className={styles.panelPills}>
                  <span className={styles.panelPill}>Instant</span>
                  <span className={styles.panelPill}>HasDuration</span>
                  <span className={styles.panelPill}>Infinite</span>
                </div>
              </div>
            </div>
            <div className={styles.panelFooter}>Single mutation layer, full audit trail.</div>
          </div>
        </div>
      </div>
    </header>
  );
}

export default function Home(): ReactNode {
  const {siteConfig} = useDocusaurusContext();
  return (
    <Layout
      title={siteConfig.title}
      description={siteConfig.tagline}>
      <HomepageHeader />
      <main>
        <section className={styles.section}>
          <div className="container">
            <div className={styles.sectionHeader}>
              <Heading as="h2">Five pillars, one language</Heading>
              <p>
                UGAS defines a clean separation between data, semantics, logic, and mutation so systems
                remain portable and predictable.
              </p>
            </div>
            <div className={styles.cardGrid}>
              <Link className={styles.linkCard} to="/docs/spec/part-ii-core-components/01-4-gameplay-controller-gc">
                <h3>Gameplay Controller</h3>
                <p className={styles.linkMeta}>The GC orchestrates interactions between components and external systems.</p>
              </Link>
              <Link className={styles.linkCard} to="/docs/spec/part-ii-core-components/02-5-attributes">
                <h3>Attributes</h3>
                <p className={styles.linkMeta}>Quantitative state with dual-value semantics for base and current values.</p>
              </Link>
              <Link className={styles.linkCard} to="/docs/spec/part-ii-core-components/04-7-gameplay-tags">
                <h3>Gameplay Tags</h3>
                <p className={styles.linkMeta}>Hierarchical labels for semantic queries, triggers, and constraints.</p>
              </Link>
              <Link className={styles.linkCard} to="/docs/spec/part-ii-core-components/05-8-gameplay-abilities">
                <h3>Gameplay Abilities</h3>
                <p className={styles.linkMeta}>Asynchronous actions with lifecycle hooks and deterministic execution.</p>
              </Link>
              <Link className={styles.linkCard} to="/docs/spec/part-ii-core-components/06-9-gameplay-effects">
                <h3>Gameplay Effects</h3>
                <p className={styles.linkMeta}>The single mutation layer that keeps state changes audited and synchronized.</p>
              </Link>
            </div>
          </div>
        </section>

        <section className={clsx(styles.section, styles.sectionAlt)}>
          <div className={clsx('container', styles.split)}>
            <div>
              <Heading as="h2">Built for engines and AI world models</Heading>
              <p>
                UGAS is designed for cross-platform interoperability. Implement it in Unreal, Unity,
                Godot, or simulated environments with consistent data and behavior.
              </p>
              <div className={styles.list}>
                <div>Event-driven architecture avoids per-frame polling.</div>
                <div>Execution policies clarify effect interaction semantics.</div>
                <div>Network replication and prediction are first-class.</div>
              </div>
            </div>
            <div className={styles.stats}>
              <div className={styles.statCard}>
                <span className={styles.statValue}>5</span>
                <span className={styles.statLabel}>Core pillars</span>
              </div>
              <div className={styles.statCard}>
                <span className={styles.statValue}>3</span>
                <span className={styles.statLabel}>Effect durations</span>
              </div>
              <div className={styles.statCard}>
                <span className={styles.statValue}>100%</span>
                <span className={styles.statLabel}>Schema-driven</span>
              </div>
            </div>
          </div>
        </section>

        <section className={styles.section}>
          <div className="container">
            <div className={styles.sectionHeader}>
              <Heading as="h2">Schema-first reference</Heading>
              <p>Validated JSON/YAML schemas keep implementations aligned across teams and tools.</p>
            </div>
            <div className={styles.cardGrid}>
              <Link className={styles.linkCard} to="/docs/spec/part-ii-core-components/01-4-gameplay-controller-gc">
                <span>Gameplay Controller</span>
                <span className={styles.linkMeta}>GC interface</span>
              </Link>
              <Link className={styles.linkCard} to="/docs/spec/part-ii-core-components/02-5-attributes">
                <span>Attributes</span>
                <span className={styles.linkMeta}>Numeric state</span>
              </Link>
              <Link className={styles.linkCard} to="/docs/spec/part-ii-core-components/05-8-gameplay-abilities">
                <span>Abilities</span>
                <span className={styles.linkMeta}>Async actions</span>
              </Link>
              <Link className={styles.linkCard} to="/docs/spec/part-ii-core-components/06-9-gameplay-effects">
                <span>Effects</span>
                <span className={styles.linkMeta}>Mutation layer</span>
              </Link>
              <Link className={styles.linkCard} to="/docs/spec/part-ii-core-components/04-7-gameplay-tags">
                <span>Gameplay Tags</span>
                <span className={styles.linkMeta}>Hierarchical labels</span>
              </Link>
            </div>
          </div>
        </section>

        <section className={clsx(styles.section, styles.ctaSection)}>
          <div className={clsx('container', styles.cta)}>
            <div>
              <Heading as="h2">Start implementing UGAS</Heading>
              <p>Explore the full spec or jump into the quick start guide.</p>
            </div>
            <div className={styles.buttons}>
              <Link className="button button--primary button--lg" to="/docs/spec">
                Full specification
              </Link>
              {/* <Link className="button button--secondary button--lg" to="/docs/intro">
                Quick start
              </Link> */}
            </div>
          </div>
        </section>
      </main>
    </Layout>
  );
}
