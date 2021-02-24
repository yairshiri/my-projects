import os
import random
import matplotlib.pyplot as plt
import neat
import pygame

pygame.init()

WIN_WIDTH = 680
WIN_HEIGHT = 460
WHITE = (255, 255, 255)
STAT_FONT = pygame.font.SysFont("comicsans", 50)

BG_IMG = pygame.transform.scale(pygame.image.load(os.path.join("dtts imgs", "background.png")), (WIN_WIDTH, WIN_HEIGHT))
BIRD_IMG = pygame.image.load(os.path.join("dtts imgs", "bird.png"))
# spikes from 66 to 355, 8 spikes
SPIKE_IMG = pygame.image.load(os.path.join("dtts imgs", "spike.png"))

icon = pygame.image.load(os.path.join("dtts imgs", "logo.png"))
pygame.display.set_icon(icon)
pygame.display.set_caption("DTTS with neat because it's neat:)")


scores = []
screen = pygame.display.set_mode((WIN_WIDTH, WIN_HEIGHT), pygame.RESIZABLE)
spikesL = []
spikesR = []
spawn = True
gen = 0
high_score = 0
append = True


class Bird:
    IMG = BIRD_IMG

    def __init__(self, x=int(WIN_WIDTH / 2), y=int(WIN_HEIGHT / 2)):
        self.x = x
        self.y = y
        self.x_velocity = 4
        self.y_velocity = 2
        self.pos = (self.x, self.y)
        self.score = 0

    def move(self):
        self.x += self.x_velocity
        if self.x <= 0:
            self.x = 0
            self.x_velocity *= -1
            self.IMG = pygame.transform.flip(self.IMG, True, False)
            self.score += 1
            num = min(self.score + 1, 5)
            create_spikes('l', random.randint(1, num))

        elif self.x >= WIN_WIDTH - self.IMG.get_width():
            self.x = WIN_WIDTH - self.IMG.get_width()
            self.x_velocity *= -1
            self.IMG = pygame.transform.flip(self.IMG, True, False)
            self.score += 1
            num = min(self.score + 1, 5)
            create_spikes('r', random.randint(1, num))
        self.y_velocity += 0.1
        self.y += self.y_velocity
        self.pos = (int(self.x), int(self.y))

    def jump(self):
        self.y_velocity = -4

    def draw(self, WIN):
        WIN.blit(self.IMG, self.pos)

    def get_mask(self):
        return pygame.mask.from_surface(self.IMG)


class Spike:
    IMG = SPIKE_IMG

    def __init__(self, index, flipped=False):
        self.y = 71 + index * 36
        if flipped:
            self.IMG = pygame.transform.flip(self.IMG, True, False)
            self.x = WIN_WIDTH - self.IMG.get_width()
        else:
            self.x = 0

        self.pos = (self.x, self.y)

    def draw(self, WIN):
        WIN.blit(self.IMG, self.pos)


def create_spikes(side, number):
    global spikesL, spikesR
    spikesR = []
    spikesL = []
    numbers = [0, 1, 2, 3, 4, 5, 6, 7, 8]
    for i in range(number):
        num = random.choice(numbers)
        if side == 'r':
            spike = Spike(num)
            if spike not in spikesR:
                spikesR.append(spike)
        elif side == 'l':
            spike = Spike(num, True)
            if spike not in spikesL:
                spikesL.append(Spike(num, True))
        numbers.remove(num)


def main():
    global spawn
    pygame.init()
    global screen
    screen = pygame.display.set_mode((WIN_WIDTH, WIN_HEIGHT))
    running = True
    screen.fill(WHITE)
    screen.blit(BG_IMG, (0, 0))
    clock = pygame.time.Clock()
    birds = [Bird()]
    while running and len(birds) > 0:
        bird = birds[0]
        clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    bird.jump()
            if event.type == pygame.QUIT:
                running = False
        # ((0,70),(680,395))
        pygame.draw.rect(screen, WHITE, (0, 70, 680, 325))
        bird.move()
        bird.draw(screen)
        for spike in spikesR:
            spike.draw(screen)
        for spike in spikesL:
            spike.draw(screen)
        check_collision(birds)
        pygame.display.update()


def eval_genomes(genomes, config):
    global screen, gen, spawn, spikesL, spikesR, high_score, scores, append
    append = True
    gen += 1
    spikesR = []
    spikesL = []
    nets = []
    birds = []
    ge = []
    for genome_id, genome in genomes:
        genome.fitness = 0
        net = neat.nn.FeedForwardNetwork.create(genome, config)
        nets.append(net)
        birds.append(Bird())
        ge.append(genome)

    running = True
    screen.fill(WHITE)
    screen.blit(BG_IMG, (0, 0))
    clock = pygame.time.Clock()
    while running and len(birds) > 0:
        clock.tick(60)
        for event in pygame.event.get():
            #           if event.type == pygame.KEYDOWN:
            #               if event.key == pygame.K_SPACE:
            #                    bird.jump()
            if event.type == pygame.QUIT:
                tmp = []
                for i, score in enumerate(scores):
                    tmp.append(i + 1)
                plt.xticks(tmp)
                _ = max(scores)
                plt.yticks(range(_ + 2))
                plt.plot(tmp, scores)
                plt.show()
                running = False
                pygame.quit()
                quit()
                break

        safe_indexes = [0, 1, 2, 3, 4, 5, 6, 7, 8]

        spikes = spikesR
        if birds[0].x_velocity > 0:
            spikes = spikesL

        for spike in spikes:
            index = int((spike.y - 71) / 36)
            if index in safe_indexes:
                safe_indexes.remove(index)

        temp = [safe_indexes[int(len(safe_indexes) / 2)], 1]
        for i in safe_indexes:
            for j in range(len(safe_indexes)):
                if i + j in safe_indexes:
                    # print(str(i).__add__(', ').__add__(str(j)))
                    if j >= temp[1] + 1:
                        temp = [i, j]
                elif i + j not in safe_indexes:
                    break

        # print(str(temp).__add__(str(safe_indexes)))
        safe_ys = []
        for i in safe_indexes:
            safe_ys.append(int(71 + i * 36))
        # ((0,70),(680,395))
        for x, bird in enumerate(birds):
            ge[x].fitness += 0.1
            bird.move()
            if bird.score > high_score:
                high_score = bird.score

            #safe_y = sorted(safe_ys, key=lambda x: abs(bird.y - x))[0]
            # print(str(bird.y).__add__(str(safe_ys)).__add__(str(bird.y - safe_y)))
            if bird.x_velocity < 0:
                x_diff = bird.x
            else:
                x_diff = WIN_WIDTH - bird.IMG.get_width() - bird.x
            from_ = 71 + temp[0] * 36
            streak = from_ + temp[1] * 36
            avg = int((from_ + streak) / 2)
            #print(str(from_).__add__(', ').__add__(str(streak)))
            output = nets[birds.index(bird)].activate(
                (int(bird.y + bird.IMG.get_height()), int(bird.y_velocity), x_diff,from_,streak))
            if output[0] > 0.25:
                bird.jump()
        ded_birds = check_collision(birds)
        draw_screen(screen, birds, spikesR, spikesL, gen, high_score)
        if len(birds) == 1 and append:
            append = False
            scores.append(birds[0].score)
        for bird in ded_birds:
            ge[birds.index(bird)].fitness -= 25
            nets.pop(birds.index(bird))
            ge.pop(birds.index(bird))
            birds.pop(birds.index(bird))


def check_collision(birds):
    ret = []
    spikes = spikesR
    spikes += spikesL
    for i, bird in enumerate(birds):
        if bird.y + bird.IMG.get_height() >= 390 or bird.y <= 75:
            ret.append(bird)
            continue
        bird_mask = bird.get_mask()
        for spike in spikes:
            offset = (spike.x - bird.x, spike.y - round(bird.y))
            spike_mask = pygame.mask.from_surface(spike.IMG)
            point = spike_mask.overlap(bird_mask, offset)
            if point:
                ret.append(bird)
                break
    return ret


def draw_screen(WIN, birds, spikes_r, spikes_l, current_gen, current_high_score):
    pygame.draw.rect(WIN, WHITE, (0, 70, 680, 325))
    for bird in birds:
        bird.draw(WIN)
    for spike in spikes_r:
        spike.draw(WIN)
    for spike in spikes_l:
        spike.draw(WIN)

    score = sorted(birds, key=lambda x: x.score, reverse=True)[0].score
    score_label = STAT_FONT.render("Score: " + str(score), 1, (0, 0, 0))
    WIN.blit(score_label, (int(WIN_WIDTH / 2), int(WIN_HEIGHT / 2) + 30))

    score_label = STAT_FONT.render("Gen: " + str(current_gen), 1, (0, 0, 0))
    WIN.blit(score_label, (int(WIN_WIDTH / 2), int(WIN_HEIGHT / 2)))

    score_label = STAT_FONT.render("Alive: " + str(len(birds)), 1, (0, 0, 0))
    WIN.blit(score_label, (int(WIN_WIDTH / 2), int(WIN_HEIGHT / 2) - 30))

    score_label = STAT_FONT.render("High score: " + str(current_high_score), 1, (0, 0, 0))
    WIN.blit(score_label, (int(WIN_WIDTH / 2), int(WIN_HEIGHT / 2) + 60))

    pygame.display.update()


def run(config_file):
    config = neat.config.Config(neat.DefaultGenome, neat.DefaultReproduction,
                                neat.DefaultSpeciesSet, neat.DefaultStagnation,
                                config_file)

    p = neat.Population(config)

    p.add_reporter(neat.StdOutReporter(True))
    stats = neat.StatisticsReporter()
    p.add_reporter(stats)

    winner = p.run(eval_genomes, 1000)

    print('\nBest genome:\n{!s}'.format(winner))


if __name__ == '__main__':
    local_dir = os.path.dirname(__file__)
    config_path = os.path.join(local_dir, 'config-feedforward dtts.txt')
    run(config_path)

