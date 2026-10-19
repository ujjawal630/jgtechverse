/**
 * JG TECHVERSE 2026 — COMPLETE WEBSITE MOTION DESIGN & GSAP INTERACTION SYSTEM
 * Production Smooth Scroll & Content Revealing Engine
 */

(function () {
    "use strict";

    // Prevent duplicate initialization
    if (window.__TV_MOTION_INITIALIZED) {
        return;
    }
    window.__TV_MOTION_INITIALIZED = true;

    // Accessibility: Check OS reduced-motion preference
    const prefersReducedMotion = window.matchMedia &&
        window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    // Global Motion API
    const TVMotion = {
        isReduced: prefersReducedMotion,
        hasGSAP: false,
        hasScrollTrigger: false,
        scrollProgressBar: null,

        // Public Refresh hook
        refresh: function () {
            if (this.hasScrollTrigger && window.ScrollTrigger) {
                window.ScrollTrigger.refresh();
            }
        },

        // Attention shake for error banner
        shakeErrorBanner: function (bannerEl) {
            const el = bannerEl || document.getElementById("stepErrorBanner");
            if (!el) return;
            el.classList.remove("tv-banner-shake");
            void el.offsetWidth; // Force reflow
            el.classList.add("tv-banner-shake");
        },

        // Copy feedback animation
        animateCopySuccess: function (buttonEl) {
            if (!buttonEl) return;
            buttonEl.classList.add("tv-copied-active");
            setTimeout(function () {
                buttonEl.classList.remove("tv-copied-active");
            }, 600);
        },

        // Programmatic Smooth Scroll with Easing
        scrollToElement: function (targetEl, callback) {
            if (!targetEl) return;

            const header = document.querySelector(".site-header") || document.querySelector("header");
            const headerHeight = header ? header.offsetHeight : 76;
            const targetY = Math.max(0, targetEl.getBoundingClientRect().top + window.pageYOffset - (headerHeight + 16));

            if (this.isReduced) {
                window.scrollTo(0, targetY);
                if (typeof callback === "function") {
                    callback();
                }
                return;
            }

            if (typeof window.gsap !== "undefined") {
                const scrollObj = { y: window.pageYOffset || document.documentElement.scrollTop };
                window.gsap.to(scrollObj, {
                    y: targetY,
                    duration: 0.85,
                    ease: "power2.inOut",
                    onUpdate: function () {
                        window.scrollTo(0, scrollObj.y);
                    },
                    onComplete: function () {
                        if (typeof callback === "function") {
                            callback();
                        }
                    }
                });
            } else {
                window.scrollTo({
                    top: targetY,
                    behavior: "smooth"
                });
                setTimeout(function () {
                    if (typeof callback === "function") {
                        callback();
                    }
                }, 650);
            }
        },

        // Content Revealing Animation on Target
        triggerContentReveal: function (targetEl) {
            if (!targetEl || this.isReduced) return;

            // 1. Add glowing highlight pulse
            targetEl.classList.remove("tv-reveal-highlight");
            void targetEl.offsetWidth; // Force reflow
            targetEl.classList.add("tv-reveal-highlight");

            setTimeout(function () {
                targetEl.classList.remove("tv-reveal-highlight");
            }, 1400);

            // 2. Animate content reveals inside target section
            if (typeof window.gsap !== "undefined") {
                const gsap = window.gsap;

                // If target is Arenas section (#arenas)
                if (targetEl.id === "arenas" || targetEl.querySelector(".tv-arenas-grid")) {
                    const cards = targetEl.querySelectorAll(".tv-arena-card");
                    if (cards.length) {
                        gsap.fromTo(cards,
                            { opacity: 0.25, y: 32, scale: 0.96 },
                            { opacity: 1, y: 0, scale: 1, duration: 0.65, stagger: 0.08, ease: "back.out(1.4)" }
                        );
                    }
                }

                // If target is Registration section (#registration)
                if (targetEl.id === "registration" || targetEl.querySelector("#teamForm")) {
                    const stepCard = targetEl.querySelector(".tv-step-card, .tv-form-step.active");
                    const stepper = targetEl.querySelector(".tv-registration-stepper");
                    if (stepCard) {
                        gsap.fromTo(stepCard,
                            { opacity: 0.35, y: 22, scale: 0.98 },
                            { opacity: 1, y: 0, scale: 1, duration: 0.55, ease: "power2.out" }
                        );
                    }
                    if (stepper) {
                        gsap.fromTo(stepper,
                            { opacity: 0.5, y: -10 },
                            { opacity: 1, y: 0, duration: 0.45, ease: "power2.out" }
                        );
                    }
                }

                // Animate Section Header if present
                const header = targetEl.querySelector(".tv-section-header") || (targetEl.classList.contains("tv-section-header") ? targetEl : null);
                if (header) {
                    const elements = header.querySelectorAll(".tv-section-eyebrow, .tv-section-title, .tv-section-lead");
                    if (elements.length) {
                        gsap.fromTo(elements,
                            { opacity: 0.3, y: 18 },
                            { opacity: 1, y: 0, duration: 0.5, stagger: 0.06, ease: "power2.out" }
                        );
                    }
                }

                // Animate items inside section (overview, process, guidelines, faq)
                const items = targetEl.querySelectorAll(".tv-process-step, .tv-guideline-card, .tv-feature-card, .tv-faq-item, details");
                if (items.length) {
                    gsap.fromTo(items,
                        { opacity: 0.35, y: 20 },
                        { opacity: 1, y: 0, duration: 0.5, stagger: 0.07, ease: "power2.out" }
                    );
                }
            }
        }
    };

    window.TVMotion = TVMotion;

    // Initialize once DOM is ready
    function initMotionSystem() {
        document.documentElement.classList.add("js-motion-ready");

        // Check for GSAP core & ScrollTrigger
        if (typeof window.gsap !== "undefined") {
            TVMotion.hasGSAP = true;
            if (typeof window.ScrollTrigger !== "undefined") {
                window.gsap.registerPlugin(window.ScrollTrigger);
                TVMotion.hasScrollTrigger = true;
                window.gsap.defaults({
                    ease: "power2.out",
                    duration: 0.6
                });
            }
        }

        // Initialize core features
        setupScrollProgressBar();
        setupSmoothScrollAndReveals();
        initHeroEntrance();
        initScrollReveals();
        initFormInteractions();
        initStudentPortalInteractions();
        initAdminInteractions();
        setupDynamicObservers();
    }

    // -------------------------------------------------------------------------
    // 1. Scroll Progress Bar
    // -------------------------------------------------------------------------
    function setupScrollProgressBar() {
        let bar = document.getElementById("tvScrollProgressBar");
        if (!bar) {
            bar = document.createElement("div");
            bar.id = "tvScrollProgressBar";
            bar.className = "tv-scroll-progress-bar";
            bar.setAttribute("aria-hidden", "true");
            document.body.prepend(bar);
        }
        TVMotion.scrollProgressBar = bar;

        let ticking = false;
        function updateScrollProgress() {
            const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
            const docHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;
            if (docHeight > 0) {
                const progress = Math.min(Math.max(scrollTop / docHeight, 0), 1);
                bar.style.transform = "scaleX(" + progress + ")";
            }
            ticking = false;
        }

        window.addEventListener("scroll", function () {
            if (!ticking) {
                window.requestAnimationFrame(updateScrollProgress);
                ticking = true;
            }
        }, { passive: true });
    }

    // -------------------------------------------------------------------------
    // 2. Global Smooth Scroll & Content Revealing Engine
    // -------------------------------------------------------------------------
    function setupSmoothScrollAndReveals() {
        // Intercept clicks on links with hashes or data-scroll-to
        document.addEventListener("click", function (e) {
            const link = e.target.closest("a, button[data-scroll-to]");
            if (!link) return;

            let targetId = null;

            if (link.hasAttribute("data-scroll-to")) {
                targetId = link.getAttribute("data-scroll-to");
            } else {
                const href = link.getAttribute("href");
                if (!href) return;

                // Handle hash links: "#arenas", "#registration", or "/#arenas"
                if (href.startsWith("#") && href.length > 1) {
                    targetId = href.substring(1);
                } else if (href.includes("#")) {
                    const currentPath = window.location.pathname;
                    const linkPath = link.pathname || "";
                    // Only intercept if target is on current page or root
                    if (linkPath === currentPath || (linkPath === "/" && currentPath === "/")) {
                        const parts = href.split("#");
                        if (parts[1]) {
                            targetId = parts[1];
                        }
                    }
                }
            }

            if (targetId) {
                const targetEl = document.getElementById(targetId) || document.querySelector(`[name="${targetId}"]`);
                if (targetEl) {
                    e.preventDefault();

                    // Close mobile navigation drawer if open
                    const toggle = document.getElementById("mobileNavToggle");
                    const drawer = document.getElementById("mobileNavDrawer");
                    const backdrop = document.getElementById("mobileDrawerBackdrop");
                    if (drawer && !drawer.hidden) {
                        drawer.hidden = true;
                        if (backdrop) backdrop.hidden = true;
                        if (toggle) {
                            toggle.setAttribute("aria-expanded", "false");
                            toggle.classList.remove("is-active");
                        }
                        document.body.classList.remove("nav-open");
                    }

                    // Perform smooth scroll and reveal
                    TVMotion.scrollToElement(targetEl, function () {
                        TVMotion.triggerContentReveal(targetEl);
                    });

                    // Update URL hash safely without triggering jump
                    if (window.history && window.history.pushState) {
                        window.history.pushState(null, null, "#" + targetId);
                    }
                }
            }
        });

        // Handle Arena Card action click: pre-select arena & reveal form
        document.querySelectorAll(".tv-arena-card-action[data-arena]").forEach(function (btn) {
            btn.addEventListener("click", function (e) {
                const arenaName = btn.getAttribute("data-arena");
                const regSection = document.getElementById("registration");
                if (regSection) {
                    e.preventDefault();
                    TVMotion.scrollToElement(regSection, function () {
                        TVMotion.triggerContentReveal(regSection);
                        // If arena checkbox exists in form, highlight or check it
                        const arenaCheckbox = document.querySelector(`input[name="arenas"][value="${arenaName}"]`);
                        if (arenaCheckbox && !arenaCheckbox.checked) {
                            arenaCheckbox.checked = true;
                            arenaCheckbox.dispatchEvent(new Event("change", { bubbles: true }));
                        }
                    });
                }
            });
        });

        // Check for hash on initial page load (e.g. /#arenas, /#registration)
        if (window.location.hash && window.location.hash.length > 1) {
            const initialId = window.location.hash.substring(1);
            const targetEl = document.getElementById(initialId);
            if (targetEl) {
                setTimeout(function () {
                    TVMotion.scrollToElement(targetEl, function () {
                        TVMotion.triggerContentReveal(targetEl);
                    });
                }, 350);
            }
        }
    }

    // -------------------------------------------------------------------------
    // 3. Signature Hero Entrance Sequence
    // -------------------------------------------------------------------------
    function initHeroEntrance() {
        const heroSection = document.getElementById("hero");
        if (!heroSection || !TVMotion.hasGSAP || TVMotion.isReduced) return;

        const livePill = heroSection.querySelector(".tv-live-pill");
        const tagline = heroSection.querySelector(".tv-hero-tagline");
        const title = heroSection.querySelector(".tv-hero-title");
        const lead = heroSection.querySelector(".tv-hero-lead");
        const metrics = heroSection.querySelectorAll(".tv-hero-metrics .tv-metric-card");
        const actions = heroSection.querySelectorAll(".tv-hero-actions > *");
        const quickLinks = heroSection.querySelector(".tv-hero-quick-links");
        const monolith = heroSection.querySelector(".tv-focal-monolith");

        const tl = window.gsap.timeline({
            delay: 0.1,
            defaults: { ease: "power3.out" }
        });

        if (livePill) {
            tl.fromTo(livePill, { opacity: 0, y: -12, scale: 0.96 }, { opacity: 1, y: 0, scale: 1, duration: 0.5 });
        }

        if (tagline) {
            tl.fromTo(tagline, { opacity: 0, y: 10, letterSpacing: "1px" }, { opacity: 1, y: 0, letterSpacing: "2.5px", duration: 0.6 }, "-=0.3");
        }

        if (title) {
            tl.fromTo(title, { opacity: 0, y: 24 }, { opacity: 1, y: 0, duration: 0.75, ease: "power3.out" }, "-=0.4");
        }

        if (lead) {
            tl.fromTo(lead, { opacity: 0, y: 16 }, { opacity: 1, y: 0, duration: 0.6 }, "-=0.45");
        }

        if (metrics && metrics.length) {
            tl.fromTo(metrics, { opacity: 0, y: 18, scale: 0.96 }, { opacity: 1, y: 0, scale: 1, duration: 0.5, stagger: 0.08, ease: "back.out(1.4)" }, "-=0.35");
        }

        if (actions && actions.length) {
            tl.fromTo(actions, { opacity: 0, y: 14 }, { opacity: 1, y: 0, duration: 0.5, stagger: 0.1 }, "-=0.3");
        }

        if (quickLinks) {
            tl.fromTo(quickLinks, { opacity: 0 }, { opacity: 1, duration: 0.5 }, "-=0.2");
        }

        if (monolith) {
            tl.fromTo(monolith, { opacity: 0, scale: 0.94, y: 20 }, { opacity: 1, scale: 1, y: 0, duration: 0.85, ease: "power2.out" }, "-=0.7");
        }
    }

    // -------------------------------------------------------------------------
    // 4. ScrollTriggered Reveals
    // -------------------------------------------------------------------------
    function initScrollReveals() {
        if (!TVMotion.hasGSAP || !TVMotion.hasScrollTrigger || TVMotion.isReduced) return;

        const gsap = window.gsap;
        const ScrollTrigger = window.ScrollTrigger;

        // Animate all Section Headers on scroll
        document.querySelectorAll(".tv-section").forEach(function (section) {
            const header = section.querySelector(".tv-section-header");
            if (header) {
                const eyebrow = header.querySelector(".tv-section-eyebrow");
                const title = header.querySelector(".tv-section-title");
                const lead = header.querySelector(".tv-section-lead");

                const elementsToAnimate = [eyebrow, title, lead].filter(Boolean);
                if (elementsToAnimate.length) {
                    gsap.fromTo(elementsToAnimate,
                        { opacity: 0, y: 22 },
                        {
                            opacity: 1,
                            y: 0,
                            duration: 0.65,
                            stagger: 0.1,
                            ease: "power2.out",
                            scrollTrigger: {
                                trigger: header,
                                start: "top 88%",
                                once: true
                            }
                        }
                    );
                }
            }
        });

        // Arenas Grid staggered cards
        const arenasGrid = document.querySelector(".tv-arenas-grid");
        if (arenasGrid) {
            const cards = arenasGrid.querySelectorAll(".tv-arena-card");
            if (cards.length) {
                gsap.fromTo(cards,
                    { opacity: 0, y: 36 },
                    {
                        opacity: 1,
                        y: 0,
                        duration: 0.65,
                        stagger: 0.08,
                        ease: "power2.out",
                        scrollTrigger: {
                            trigger: arenasGrid,
                            start: "top 85%",
                            once: true
                        }
                    }
                );
            }
        }

        // Overview / Process / Guidelines staggered entrance
        ["#overview", "#process", "#guidelines"].forEach(function (secId) {
            const sec = document.querySelector(secId);
            if (!sec) return;
            const items = sec.querySelectorAll(".tv-process-step, .tv-guideline-card, .tv-feature-card, .tv-spec-card, .tv-standard-item");
            if (items.length) {
                gsap.fromTo(items,
                    { opacity: 0, y: 24 },
                    {
                        opacity: 1,
                        y: 0,
                        duration: 0.6,
                        stagger: 0.08,
                        ease: "power2.out",
                        scrollTrigger: {
                            trigger: sec,
                            start: "top 82%",
                            once: true
                        }
                    }
                );
            }
        });

        // FAQ Items Accordion entrance
        const faqSection = document.getElementById("faq");
        if (faqSection) {
            const faqItems = faqSection.querySelectorAll(".tv-faq-item, details");
            if (faqItems.length) {
                gsap.fromTo(faqItems,
                    { opacity: 0, y: 18 },
                    {
                        opacity: 1,
                        y: 0,
                        duration: 0.5,
                        stagger: 0.06,
                        ease: "power2.out",
                        scrollTrigger: {
                            trigger: faqSection,
                            start: "top 85%",
                            once: true
                        }
                    }
                );
            }
        }
    }

    // -------------------------------------------------------------------------
    // 5. Form Microinteractions & Dynamic Form Lifecycles
    // -------------------------------------------------------------------------
    function initFormInteractions() {
        // Smooth transitions between form steps
        const stepPills = document.querySelectorAll(".tv-stepper-pill");
        stepPills.forEach(function (pill) {
            pill.addEventListener("click", function () {
                if (TVMotion.hasGSAP) {
                    window.gsap.fromTo(pill, { scale: 0.95 }, { scale: 1, duration: 0.3, ease: "back.out(2)" });
                }
            });
        });

        // Stepper advance animation
        document.querySelectorAll(".step-next-btn, .step-prev-btn").forEach(function (btn) {
            btn.addEventListener("click", function () {
                setTimeout(function () {
                    const activeStep = document.querySelector(".tv-form-step.active");
                    if (activeStep && TVMotion.hasGSAP) {
                        window.gsap.fromTo(activeStep,
                            { opacity: 0, y: 14 },
                            { opacity: 1, y: 0, duration: 0.4, ease: "power2.out" }
                        );
                    }
                }, 50);
            });
        });

        // Success Modal Popup Animation
        const successModal = document.getElementById("registrationSuccessModal");
        if (successModal) {
            const observer = new MutationObserver(function () {
                if (!successModal.classList.contains("hidden")) {
                    const card = successModal.querySelector(".success-modal-card");
                    if (card && TVMotion.hasGSAP) {
                        window.gsap.fromTo(card,
                            { opacity: 0, scale: 0.9, y: 20 },
                            { opacity: 1, scale: 1, y: 0, duration: 0.5, ease: "back.out(1.5)" }
                        );
                    }
                }
            });
            observer.observe(successModal, { attributes: true, attributeFilter: ["class"] });
        }
    }

    // -------------------------------------------------------------------------
    // 6. Dynamic Observers for Dynamically Added DOM Elements
    // -------------------------------------------------------------------------
    function setupDynamicObservers() {
        const membersBody = document.getElementById("membersBody");
        if (membersBody) {
            const memberObserver = new MutationObserver(function (mutations) {
                mutations.forEach(function (mutation) {
                    mutation.addedNodes.forEach(function (node) {
                        if (node.nodeType === 1 && node.tagName === "TR") {
                            if (TVMotion.hasGSAP) {
                                window.gsap.fromTo(node,
                                    { opacity: 0, y: 12 },
                                    { opacity: 1, y: 0, duration: 0.35, ease: "power2.out" }
                                );
                            }
                            TVMotion.refresh();
                        }
                    });
                });
            });
            memberObserver.observe(membersBody, { childList: true });
        }

        const projectsContainer = document.getElementById("projectsContainer");
        if (projectsContainer) {
            const projectObserver = new MutationObserver(function (mutations) {
                mutations.forEach(function (mutation) {
                    mutation.addedNodes.forEach(function (node) {
                        if (node.nodeType === 1 && node.classList && node.classList.contains("multi-project-card")) {
                            if (TVMotion.hasGSAP) {
                                window.gsap.fromTo(node,
                                    { opacity: 0, y: 20, scale: 0.98 },
                                    { opacity: 1, y: 0, scale: 1, duration: 0.45, ease: "power2.out" }
                                );
                            }
                            TVMotion.refresh();
                        }
                    });
                });
            });
            projectObserver.observe(projectsContainer, { childList: true });
        }
    }

    // -------------------------------------------------------------------------
    // 7. Student Portal & Details Page Microinteractions
    // -------------------------------------------------------------------------
    function initStudentPortalInteractions() {
        if (!TVMotion.hasGSAP) return;
        const gsap = window.gsap;

        // Dashboard & Registry Hero
        const dashHero = document.querySelector(".tv-dash-hero, .team-profile-hero, .dossier-hero");
        if (dashHero) {
            gsap.fromTo(dashHero,
                { opacity: 0, y: 18 },
                { opacity: 1, y: 0, duration: 0.55, ease: "power2.out" }
            );
        }

        // Credential Lookup Box
        const lookupBox = document.querySelector(".tv-lookup-full-box, .lookup-form");
        if (lookupBox) {
            gsap.fromTo(lookupBox,
                { opacity: 0, y: 16 },
                { opacity: 1, y: 0, duration: 0.5, delay: 0.12, ease: "power2.out" }
            );
        }

        // Official Printable ID Card
        const idCard = document.querySelector(".official-id-card");
        if (idCard) {
            gsap.fromTo(idCard,
                { opacity: 0, scale: 0.94, y: 22 },
                { opacity: 1, scale: 1, y: 0, duration: 0.7, ease: "back.out(1.3)" }
            );
        }

        // Multi-Project Dossier Cards in Team Details
        const projectCards = document.querySelectorAll(".tv-project-dossier-card, .project-card");
        if (projectCards.length) {
            gsap.fromTo(projectCards,
                { opacity: 0, y: 20 },
                { opacity: 1, y: 0, duration: 0.5, stagger: 0.08, ease: "power2.out" }
            );
        }

        // Copy button interactions across portal
        document.querySelectorAll("[data-copy-target], .copy-btn, .btn-copy, .tv-copy-btn, .tv-github-copy-btn").forEach(function (btn) {
            btn.addEventListener("click", function () {
                TVMotion.animateCopySuccess(btn);
            });
        });
    }

    // -------------------------------------------------------------------------
    // 8. Administrative & Judge Console Motion (Restrained & Productive)
    // -------------------------------------------------------------------------
    function initAdminInteractions() {
        if (!TVMotion.hasGSAP) return;
        const gsap = window.gsap;

        // Staff Sign-in Card
        const loginCard = document.querySelector(".admin-login-card");
        if (loginCard) {
            gsap.fromTo(loginCard,
                { opacity: 0, scale: 0.96, y: 16 },
                { opacity: 1, scale: 1, y: 0, duration: 0.5, ease: "power2.out" }
            );
        }

        // Admin Topbar
        const adminTopbar = document.querySelector(".admin-topbar");
        if (adminTopbar) {
            gsap.fromTo(adminTopbar,
                { opacity: 0, y: -8 },
                { opacity: 1, y: 0, duration: 0.4, ease: "power2.out" }
            );
        }

        // KPI Metric Cards
        const kpiCards = document.querySelectorAll(".admin-kpi-card, .kpi-metric-card");
        if (kpiCards.length) {
            gsap.fromTo(kpiCards,
                { opacity: 0, y: 12 },
                { opacity: 1, y: 0, duration: 0.4, stagger: 0.04, ease: "power2.out" }
            );
        }

        // Arena domain cards in admin arena overview
        const domainCards = document.querySelectorAll(".admin-domain-card");
        if (domainCards.length) {
            gsap.fromTo(domainCards,
                { opacity: 0, y: 16 },
                { opacity: 1, y: 0, duration: 0.45, stagger: 0.05, ease: "power2.out" }
            );
        }
    }

    // Run when ready
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initMotionSystem);
    } else {
        initMotionSystem();
    }

})();
