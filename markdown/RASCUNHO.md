# Project draft — Hack Brasil 2026

## Project name

CyberCheck

## Tagline / summary

Helps independent developers and small teams find security issues in their projects and understand what to fix first.

## Track

Cybersecurity

## Project description

### Problem to solve

Independent developers and small teams need to secure the systems they build, even without dedicated security specialists. Beyond finding potential code vulnerabilities, they need to check the libraries they use, exposed credentials, and configurations that could put their projects at risk.

The challenge we want to address is turning these checks into practical decisions: where the problem is, what impact it could have, what needs attention first, and how to start fixing it. An isolated technical alert can require investigation and security knowledge that a developer may not yet have.

There is also the risk of relying on a discontinued library or one whose repository has been archived. In those cases, upgrading the version may not be enough: the developer needs to assess possible replacements and understand the changes required.

### Target audience

Independent developers and small teams maintaining their own or their clients' projects who want to incorporate security checks into development. The initial focus will be Python projects, without limiting the proposal to websites or web applications.

### Objective and proposed solution

CyberCheck aims to present security issues clearly, grouped by type and ordered by priority, with evidence and suggested actions. Its objective is to help developers understand identified risks and make remediation decisions more independently.

Users will be able to connect GitHub, authorize the repositories they want assessed, and start an analysis. Each issue will include its location where applicable, potential impact, and remediation guidance. Results will identify the code revision and analysis date, allowing users to follow up with new assessments after making changes.

### Initial version

The MVP will cover three areas:

- **Code:** look for potential vulnerabilities such as SQL and command injection, unsafe code execution, and unsafe data loading.
- **Dependencies:** identify versions with known vulnerabilities, discontinuation notices, and archived repositories, suggesting upgrades or possible alternatives when needed.
- **Secrets and configuration:** look for exposed credentials and potentially insecure settings.

The deliverable will focus on exposing issues and guiding action. Each finding will include evidence and explicit uncertainty to distinguish a suspected issue from a confirmed vulnerability. The absence of alerts will not be presented as a security guarantee.

### Expected impact

We want to make alerts easier to interpret and help developers decide where to start, bringing security checks into the everyday work of small development teams. The proposal's usefulness will be assessed through the clarity of results, the relevance of guidance, and its ability to support fixes in analyzed projects.

### Future development

After validating the initial assessment, we intend to explore monitoring new security advisories and notifying the owners of potentially affected projects. This is outside the first version.

### Responsible use

The proposal has a defensive purpose. Analyses and demonstrations will use projects we own or have written authorization to assess, without exposing real third-party personal data. Access will be limited to repositories authorized by the user.
