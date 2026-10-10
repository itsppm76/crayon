# Personal-site integration staging

Base personal efeb4e3bd10008f6c0fdb565e7a1dcbc7c514785. Reviewed source team e319dc7fc1bd8df9eb05feb35f982b1fad60ea9d. This is a selective release port, not a repository replacement or full feature acceptance.

Included: PDF/DOCX/Markdown/PPTX visible-chat exports, research focus/deep source reads, fetched numeric cards, web goals/followups, insert-only reviewed-email decision audit plus erasure, and unmounted durable voice ticket/state/final/recovery source and tests. Preserved personal Firebase/auth/session/Google private-result isolation, API origin, staged attachments, named history and existing bot startup. Source provenance: team PRs9-11,14-17. Export HTML line-break fix merged to team in PR18 at b6d2f916a1b8caebd9547560c1e5d0126efd4061.

Manifest is scoped to /crayon/, uses existing Crayon artwork, no service worker or offline/private response caching. No Digital Asset Links file is included: actual APK signing certificate/package verification is still required. Manifest publication alone is not proof of Android installability or verified TWA association.

Image generation is dropped from this release under the owner's free-only condition. Google's official Gemini2.5FlashImage pricing says Free Tier Not available for input/output, standard paid output $0.039/image: https://ai.google.dev/gemini-api/docs/pricing . Image/file analysis remains unchanged. No paid API/card/key activation.

Remaining: isolate and port latest peer browser-code/charts/read-only sharing/currency/stocks features into authenticated personal boundaries; native live voice ASGI/consent/device tests; WhatsApp owner/resource/provider delivery+canonical inbox/receipt integration. Disabled #12/#13 scaffolds are not merged or enabled. No whole-file copy of stale team personal snapshot. Current live app/main untouched until reviewed acceptance and release checkpoint.

Proof: 524 inherited/private tests and four personal release contract tests; local browser390/1280 with mocked auth, no real login/provider send, 4download exports each width, UI/icon/PDF pixels inspected. These checks are staging evidence, not live provider/device acceptance.

Text-only packaging: manifest references the unchanged existing crayon.svg (sizes:any), not newly generated PNGs. SVG manifests are supported by the manifest spec, but Android/TWA installability remains unverified. Vendored export library bytes remain unchanged (each file under 1 MB), no CDN or dependency changes.

CDN packaging: docx 8.5.0, jsPDF 2.5.1 and PptxGenJS 3.12.0 load from pinned URLs with SHA384 SRI and anonymous CORS. Downloaded upstream bytes were compared exactly to the formerly vendored files. Export libraries now need network availability; offline PDF/DOCX/PPTX export is not guaranteed. Markdown export remains local.
