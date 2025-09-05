// Dashboard JavaScript - RXbot

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Auto-refresh stats every 30 seconds
    if (window.location.pathname === '/') {
        setInterval(refreshStats, 30000);
    }

    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Add loading animation to buttons on click
    document.querySelectorAll('.btn').forEach(button => {
        button.addEventListener('click', function() {
            if (this.type !== 'button' || this.getAttribute('data-bs-toggle')) return;
            
            const originalText = this.innerHTML;
            this.innerHTML = '<span class="loading"></span> Carregando...';
            this.disabled = true;
            
            setTimeout(() => {
                this.innerHTML = originalText;
                this.disabled = false;
            }, 2000);
        });
    });

    // Highlight active navigation item
    highlightActiveNav();

    // Search functionality for commands
    if (document.querySelector('#commandSearch')) {
        setupCommandSearch();
    }

    // FAQ search functionality
    if (document.querySelector('#faqSearch')) {
        setupFaqSearch();
    }

    // Copy command to clipboard
    setupCommandCopy();

    // Initialize animations
    initScrollAnimations();
});

// Refresh stats from API
function refreshStats() {
    fetch('/api/stats')
        .then(response => response.json())
        .then(data => {
            updateStatCards(data);
        })
        .catch(error => {
            console.log('Stats refresh failed:', error);
        });
}

// Update stat cards with new data
function updateStatCards(stats) {
    const statElements = {
        'total_commands': document.querySelector('[data-stat="commands"] h3'),
        'total_users': document.querySelector('[data-stat="users"] h3'),
        'total_copinhas': document.querySelector('[data-stat="copinhas"] h3'),
        'total_tickets': document.querySelector('[data-stat="tickets"] h3')
    };

    Object.keys(statElements).forEach(key => {
        const element = statElements[key];
        if (element && stats[key] !== undefined) {
            animateNumber(element, parseInt(element.textContent), stats[key]);
        }
    });
}

// Animate number change
function animateNumber(element, from, to) {
    const duration = 1000;
    const startTime = Date.now();
    
    function updateNumber() {
        const elapsed = Date.now() - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const current = Math.floor(from + (to - from) * progress);
        
        element.textContent = current.toLocaleString();
        
        if (progress < 1) {
            requestAnimationFrame(updateNumber);
        }
    }
    
    updateNumber();
}

// Highlight active navigation item
function highlightActiveNav() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav-link');
    
    navLinks.forEach(link => {
        const href = link.getAttribute('href');
        if (href === currentPath || (currentPath === '/' && href === '/')) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });
}

// Setup command search functionality
function setupCommandSearch() {
    const searchInput = document.getElementById('commandSearch');
    const commandCards = document.querySelectorAll('.command-item');
    
    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase();
        
        commandCards.forEach(card => {
            const commandName = card.querySelector('.command-name').textContent.toLowerCase();
            const commandDesc = card.querySelector('.command-description').textContent.toLowerCase();
            
            if (commandName.includes(searchTerm) || commandDesc.includes(searchTerm)) {
                card.closest('.col-lg-6').style.display = 'block';
            } else {
                card.closest('.col-lg-6').style.display = 'none';
            }
        });
        
        // Show/hide categories based on visible commands
        document.querySelectorAll('.command-category').forEach(category => {
            const visibleCommands = category.querySelectorAll('.col-lg-6[style*="block"], .col-lg-6:not([style*="none"])');
            category.style.display = visibleCommands.length > 0 ? 'block' : 'none';
        });
    });
}

// Setup FAQ search functionality
function setupFaqSearch() {
    const searchInput = document.getElementById('faqSearch');
    const faqItems = document.querySelectorAll('.accordion-item');
    
    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase();
        
        faqItems.forEach(item => {
            const question = item.querySelector('.accordion-button').textContent.toLowerCase();
            const answer = item.querySelector('.accordion-body').textContent.toLowerCase();
            
            if (question.includes(searchTerm) || answer.includes(searchTerm)) {
                item.style.display = 'block';
            } else {
                item.style.display = 'none';
            }
        });
    });
}

// Setup command copy functionality
function setupCommandCopy() {
    document.querySelectorAll('.command-name code').forEach(codeElement => {
        codeElement.style.cursor = 'pointer';
        codeElement.title = 'Clique para copiar';
        
        codeElement.addEventListener('click', function() {
            const commandText = this.textContent;
            
            navigator.clipboard.writeText(commandText).then(() => {
                // Show success message
                showToast('Comando copiado!', 'success');
            }).catch(() => {
                // Fallback for older browsers
                const textArea = document.createElement('textarea');
                textArea.value = commandText;
                document.body.appendChild(textArea);
                textArea.select();
                document.execCommand('copy');
                document.body.removeChild(textArea);
                
                showToast('Comando copiado!', 'success');
            });
        });
    });
}

// Show toast notification
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast position-fixed top-0 end-0 m-3 bg-${type} text-white`;
    toast.style.zIndex = '1050';
    toast.innerHTML = `
        <div class="toast-body">
            <i class="fas fa-check-circle me-2"></i>
            ${message}
        </div>
    `;
    
    document.body.appendChild(toast);
    
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    toast.addEventListener('hidden.bs.toast', () => {
        document.body.removeChild(toast);
    });
}

// Initialize scroll animations
function initScrollAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);
    
    // Animate cards on scroll
    document.querySelectorAll('.card, .alert').forEach(element => {
        element.style.opacity = '0';
        element.style.transform = 'translateY(20px)';
        element.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(element);
    });
}

// Theme toggle (future feature)
function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
}

// Load saved theme
function loadTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
}

// Back to top button
function addBackToTop() {
    const backToTopButton = document.createElement('button');
    backToTopButton.innerHTML = '<i class="fas fa-arrow-up"></i>';
    backToTopButton.className = 'btn btn-primary position-fixed';
    backToTopButton.style.cssText = `
        bottom: 20px;
        right: 20px;
        z-index: 1000;
        border-radius: 50%;
        width: 50px;
        height: 50px;
        display: none;
    `;
    
    document.body.appendChild(backToTopButton);
    
    // Show/hide based on scroll position
    window.addEventListener('scroll', () => {
        if (window.pageYOffset > 300) {
            backToTopButton.style.display = 'block';
        } else {
            backToTopButton.style.display = 'none';
        }
    });
    
    // Scroll to top on click
    backToTopButton.addEventListener('click', () => {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    });
}

// Initialize back to top button
addBackToTop();

// Performance monitoring
function logPerformance() {
    if ('performance' in window) {
        window.addEventListener('load', () => {
            setTimeout(() => {
                const perfData = performance.getEntriesByType('navigation')[0];
                console.log(`Page loaded in ${perfData.loadEventEnd - perfData.fetchStart}ms`);
            }, 0);
        });
    }
}

// Initialize performance monitoring
logPerformance();