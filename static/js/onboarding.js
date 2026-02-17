/**
 * Onboarding Tour with Intro.js
 * Provides interactive tours for first-time users
 */

// Tour steps for dashboard page
const tourSteps = {
  dashboard: [
    {
      intro: "Welcome to Course Builder Studio! Let's take a quick tour to help you get started building your course.",
    },
    {
      element: '#create-course-btn',
      intro: "Create your first course here. You'll start by defining learning outcomes and generating a course structure.",
    },
    {
      element: '.sidebar-nav',
      intro: "Navigate between pages using this menu. The workflow goes: Planner → Builder → Studio → Textbook → Publish.",
    },
    {
      element: '#help-menu-btn',
      intro: "Access help resources and replay this tour anytime from this menu.",
    }
  ],

  planner: [
    {
      intro: "Welcome to the Planner! This is where you define your course structure.",
    },
    {
      element: '#outcomes-tab',
      intro: "Start by defining learning outcomes first. What should students be able to do after completing your course?",
    },
    {
      element: '#blueprint-tab',
      intro: "Generate your course structure with AI. The system will create modules and lessons based on your outcomes.",
    },
    {
      element: '.bloom-selector',
      intro: "Set cognitive levels using Bloom's taxonomy. This helps ensure appropriate difficulty progression.",
      position: 'bottom'
    }
  ],

  studio: [
    {
      intro: "Welcome to the Studio! This is where you edit and generate activity content.",
    },
    {
      element: '.activity-list',
      intro: "Select activities from this list to edit their content. Each activity represents a learning component.",
    },
    {
      element: '.content-preview',
      intro: "Preview and edit generated content here. You can manually edit or use AI assistance.",
    },
    {
      element: '#generate-btn',
      intro: "Generate content with AI using this button. The system creates pedagogically sound content based on your outcomes.",
    },
    {
      element: '.ai-toolbar',
      intro: "Use the AI toolbar to improve selected text. You can expand, simplify, fix grammar, or provide custom instructions.",
      position: 'bottom'
    }
  ],

  builder: [
    {
      intro: "Welcome to the Builder! This is where you manage your course structure.",
    },
    {
      element: '.course-tree',
      intro: "Your course hierarchy is shown here. Expand modules to see lessons and activities.",
    },
    {
      element: '.add-module-btn',
      intro: "Add new modules, lessons, and activities using these buttons.",
    }
  ],

  textbook: [
    {
      intro: "Welcome to the Textbook Generator! Create comprehensive learning materials for your course.",
    },
    {
      element: '#generate-textbook-btn',
      intro: "Generate a complete textbook based on your course content and learning outcomes.",
    }
  ],

  publish: [
    {
      intro: "Welcome to Publish! Export your completed course in various formats.",
    },
    {
      element: '.export-options',
      intro: "Choose from multiple export formats including SCORM, PDF, and Canvas LMS.",
    }
  ]
};

/**
 * Initialize onboarding for a specific page
 * @param {string} pageName - The page identifier (dashboard, planner, studio, etc.)
 */
function initOnboarding(pageName = 'dashboard') {
  // Check if user has completed or skipped onboarding
  const completed = localStorage.getItem('onboarding_completed');
  const skipped = localStorage.getItem('onboarding_skipped');

  // Don't auto-start if already completed or skipped
  if (completed || skipped) {
    return;
  }

  // Only auto-start on dashboard
  if (pageName !== 'dashboard') {
    return;
  }

  // Wait for page to fully load
  setTimeout(() => {
    startTour(pageName);
  }, 500);
}

/**
 * Start a tour for a specific page
 * @param {string} pageName - The page identifier
 */
function startTour(pageName = 'dashboard') {
  const steps = tourSteps[pageName];

  if (!steps || steps.length === 0) {
    console.warn(`No tour steps defined for page: ${pageName}`);
    return;
  }

  // Initialize Intro.js
  const intro = introJs();

  intro.setOptions({
    steps: steps,
    showProgress: true,
    showBullets: false,
    exitOnOverlayClick: false,
    disableInteraction: true,
    nextLabel: 'Next →',
    prevLabel: '← Back',
    doneLabel: 'Done',
  });

  // Handle tour completion
  intro.oncomplete(() => {
    localStorage.setItem('onboarding_completed', 'true');
    localStorage.removeItem('onboarding_skipped');
  });

  // Handle tour exit
  intro.onexit(() => {
    if (!localStorage.getItem('onboarding_completed')) {
      localStorage.setItem('onboarding_skipped', 'true');
    }
  });

  intro.start();
}

/**
 * Reset onboarding state (for testing or user request)
 */
function resetOnboarding() {
  localStorage.removeItem('onboarding_completed');
  localStorage.removeItem('onboarding_skipped');
}

// Export functions
window.onboarding = {
  init: initOnboarding,
  start: startTour,
  reset: resetOnboarding
};

// Auto-initialize on page load
document.addEventListener('DOMContentLoaded', () => {
  // Detect page from body class or data attribute
  const body = document.body;
  let pageName = 'dashboard';

  if (body.classList.contains('page-planner')) pageName = 'planner';
  else if (body.classList.contains('page-studio')) pageName = 'studio';
  else if (body.classList.contains('page-builder')) pageName = 'builder';
  else if (body.classList.contains('page-textbook')) pageName = 'textbook';
  else if (body.classList.contains('page-publish')) pageName = 'publish';
  else if (body.classList.contains('page-dashboard')) pageName = 'dashboard';

  initOnboarding(pageName);
});
