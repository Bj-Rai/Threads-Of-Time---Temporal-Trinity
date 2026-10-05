import pygame


def show_completion_certificate(game):
    district = game.current_district
    max_width = game.screen.get_width() - 80
    max_height = game.screen.get_height() - 40
    if game.certificate_image is not None:
        scale = min(
            max_width / game.certificate_image.get_width(),
            max_height / game.certificate_image.get_height(),
        )
        certificate_size = (
            int(game.certificate_image.get_width() * scale),
            int(game.certificate_image.get_height() * scale),
        )
        certificate = pygame.transform.smoothscale(game.certificate_image, certificate_size)
    else:
        certificate_size = (min(max_width, 900), min(max_height, 560))
        certificate = pygame.Surface(certificate_size)
        certificate.fill((255, 245, 220))
        pygame.draw.rect(certificate, (105, 35, 12), certificate.get_rect(), 8)
        pygame.draw.rect(certificate, (190, 130, 45), certificate.get_rect().inflate(-24, -24), 3)

    cert_rect = certificate.get_rect(center=game.screen.get_rect().center)

    for alpha in range(0, 255, 15):
        overlay = pygame.Surface(game.screen.get_size(), pygame.SRCALPHA)
        overlay.set_alpha(alpha)
        overlay.fill((0, 0, 0))
        game.screen.blit(overlay, (0, 0))
        game.screen.blit(certificate, cert_rect)

        game.add_particles(cert_rect.centerx, cert_rect.centery, (255, 215, 0), 5)
        pygame.display.flip()
        pygame.time.wait(20)

    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game.running = False
                return
            if event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.KEYDOWN:
                waiting = False
