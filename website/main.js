/**
 * CellOS Website Main JavaScript
 * Handles interactivity, animations, and dynamic content
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize components
    initNavigation();
    initTabs();
    initScrollEffects();
    initCellAnimation();
    initMobileMenu();
});

/**
 * Initialize navigation functionality
 */
function initNavigation() {
    // Add scroll class to header when scrolled
    window.addEventListener('scroll', function() {
        const header = document.querySelector('header');
        if (window.scrollY > 50) {
            header.classList.add('scrolled');
        } else {
            header.classList.remove('scrolled');
        }
    });

    // Smooth scroll for navigation links
    document.querySelectorAll('a[href^="#"]:not([href="#"])').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            
            if (targetId === '#') return;
            
            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                const headerHeight = document.querySelector('header').offsetHeight;
                const targetPosition = targetElement.getBoundingClientRect().top + window.pageYOffset - headerHeight;
                
                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth'
                });
                
                // Close mobile menu if open
                document.querySelector('.nav-links').classList.remove('active');
                document.querySelector('.mobile-menu-btn').classList.remove('active');
            }
        });
    });
}

/**
 * Initialize tabs in the technology section
 */
function initTabs() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Remove active class from all buttons and panes
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabPanes.forEach(pane => pane.classList.remove('active'));
            
            // Add active class to clicked button
            this.classList.add('active');
            
            // Show corresponding tab pane
            const tabId = this.getAttribute('data-tab');
            document.getElementById(tabId).classList.add('active');
        });
    });
}

/**
 * Initialize scroll effects for animations
 */
function initScrollEffects() {
    // Get all elements to be animated
    const elements = document.querySelectorAll('.vision-card, .tech-component, .application-card, .blog-card, .involvement-card');
    
    // Create an Intersection Observer
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in');
                observer.unobserve(entry.target);
            }
        });
    }, {
        root: null,
        threshold: 0.1,
        rootMargin: '0px 0px -100px 0px'
    });
    
    // Observe each element
    elements.forEach(element => {
        observer.observe(element);
    });
    
    // Add animation classes with delays
    document.querySelectorAll('.vision-card, .tech-component, .application-card').forEach((element, index) => {
        element.classList.add(`delay-${(index % 3) + 1}`);
    });
}

/**
 * Initialize the cell animation in the hero section
 */
function initCellAnimation() {
    const container = document.getElementById('cellAnimation');
    if (!container) return;
    
    // Configuration
    const config = {
        cellCount: 30,
        cellSizeMin: 10,
        cellSizeMax: 40,
        speedMin: 0.5,
        speedMax: 2,
        connectionDistance: 100,
        containerWidth: container.offsetWidth,
        containerHeight: container.offsetHeight
    };
    
    // Create cells
    const cells = [];
    for (let i = 0; i < config.cellCount; i++) {
        createCell(cells, config, container);
    }
    
    // Animation loop
    function animate() {
        // Clear canvas for redrawing
        const canvas = document.getElementById('cellCanvas');
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // Draw connections first (behind cells)
        drawConnections(cells, ctx, config);
        
        // Update and draw cells
        cells.forEach(cell => {
            // Update position
            cell.x += cell.vx;
            cell.y += cell.vy;
            
            // Bounce off walls
            if (cell.x <= cell.size || cell.x >= config.containerWidth - cell.size) {
                cell.vx = -cell.vx;
            }
            if (cell.y <= cell.size || cell.y >= config.containerHeight - cell.size) {
                cell.vy = -cell.vy;
            }
            
            // Draw cell
            ctx.beginPath();
            ctx.arc(cell.x, cell.y, cell.size, 0, Math.PI * 2);
            ctx.fillStyle = cell.color;
            ctx.fill();
        });
        
        requestAnimationFrame(animate);
    }
    
    // Set up canvas
    const canvas = document.createElement('canvas');
    canvas.id = 'cellCanvas';
    canvas.width = config.containerWidth;
    canvas.height = config.containerHeight;
    container.appendChild(canvas);
    
    // Start animation
    animate();
    
    // Handle window resize
    window.addEventListener('resize', () => {
        config.containerWidth = container.offsetWidth;
        config.containerHeight = container.offsetHeight;
        canvas.width = config.containerWidth;
        canvas.height = config.containerHeight;
        
        // Reposition cells if container size changed significantly
        cells.forEach(cell => {
            if (cell.x > config.containerWidth) cell.x = config.containerWidth - cell.size;
            if (cell.y > config.containerHeight) cell.y = config.containerHeight - cell.size;
        });
    });
}

/**
 * Create a single cell for the animation
 */
function createCell(cells, config, container) {
    const size = Math.random() * (config.cellSizeMax - config.cellSizeMin) + config.cellSizeMin;
    const cell = {
        x: Math.random() * (config.containerWidth - size * 2) + size,
        y: Math.random() * (config.containerHeight - size * 2) + size,
        size: size,
        vx: (Math.random() - 0.5) * (config.speedMax - config.speedMin) + config.speedMin,
        vy: (Math.random() - 0.5) * (config.speedMax - config.speedMin) + config.speedMin,
        color: getRandomColor(0.2)
    };
    
    cells.push(cell);
}

/**
 * Draw connections between nearby cells
 */
function drawConnections(cells, ctx, config) {
    for (let i = 0; i < cells.length; i++) {
        for (let j = i + 1; j < cells.length; j++) {
            const dx = cells[i].x - cells[j].x;
            const dy = cells[i].y - cells[j].y;
            const distance = Math.sqrt(dx * dx + dy * dy);
            
            if (distance < config.connectionDistance) {
                // Calculate opacity based on distance
                const opacity = 1 - (distance / config.connectionDistance);
                
                ctx.beginPath();
                ctx.moveTo(cells[i].x, cells[i].y);
                ctx.lineTo(cells[j].x, cells[j].y);
                ctx.strokeStyle = `rgba(79, 70, 229, ${opacity * 0.3})`;
                ctx.lineWidth = 1;
                ctx.stroke();
            }
        }
    }
}

/**
 * Generate a random color with specified opacity
 */
function getRandomColor(opacity) {
    const hue = Math.floor(Math.random() * 60) + 220; // Blue to purple range
    return `hsla(${hue}, 80%, 60%, ${opacity})`;
}

/**
 * Initialize mobile menu functionality
 */
function initMobileMenu() {
    const menuButton = document.querySelector('.mobile-menu-btn');
    const navLinks = document.querySelector('.nav-links');
    
    if (!menuButton || !navLinks) return;
    
    menuButton.addEventListener('click', function() {
        this.classList.toggle('active');
        
        if (navLinks.classList.contains('active')) {
            // Menu is open, close it
            navLinks.style.height = '0';
            setTimeout(() => {
                navLinks.classList.remove('active');
                navLinks.style.height = '';
            }, 300);
        } else {
            // Menu is closed, open it
            navLinks.classList.add('active');
            const height = navLinks.scrollHeight;
            navLinks.style.height = '0';
            
            // Trigger reflow
            navLinks.offsetHeight;
            
            navLinks.style.height = `${height}px`;
        }
    });
    
    // Add mobile menu styles
    const style = document.createElement('style');
    style.innerHTML = `
        @media (max-width: 768px) {
            .nav-links {
                position: absolute;
                top: var(--header-height);
                left: 0;
                width: 100%;
                background-color: white;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                flex-direction: column;
                overflow: hidden;
                height: 0;
                transition: height var(--transition-normal);
            }
            
            .nav-links.active {
                display: flex;
                height: auto;
            }
            
            .nav-links a {
                margin: 0;
                padding: 1rem 2rem;
                border-bottom: 1px solid var(--color-gray-light);
            }
            
            .mobile-menu-btn.active span:nth-child(1) {
                transform: rotate(45deg) translate(5px, 5px);
            }
            
            .mobile-menu-btn.active span:nth-child(2) {
                opacity: 0;
            }
            
            .mobile-menu-btn.active span:nth-child(3) {
                transform: rotate(-45deg) translate(5px, -5px);
            }
        }
    `;
    document.head.appendChild(style);
}
