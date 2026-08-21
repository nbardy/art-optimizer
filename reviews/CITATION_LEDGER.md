# Canonical Citation Ledger

This ledger is the source-of-truth bibliography for the review corpus. It records source type so essays, prototypes, preprints, theses, and peer-reviewed papers are not cited as though they carry identical evidence.

## Source-type key

| Label | Meaning |
|---|---|
| Peer reviewed | archival conference/journal/workshop publication |
| Thesis | university dissertation with detailed methods/evaluation |
| Preprint | public manuscript without an archival venue identified here |
| Author essay | public technical/research essay by the project author |
| Source code | released implementation; supports implementation claims, not independent evaluation |
| Project page | official author/institution page; useful for media, abstracts, and canonical links |

# A. Generative recommendation and persistent preference

## `MURDOCK-GR`

**Type:** Author essay  
**Canonical citation:**

> Ryn Murdock. “Generative Recommenders.” 5 April 2024, with later revisions. https://rynmurdock.github.io/writing/generative_recommenders.html

**Use for:** Zahir framing; collaborative preference-to-generation bridge; qualitative iterative feedback; artist-as-curator concept; explicit scaling limitations; link to follow-up preference-prior work.

**Do not use for:** peer-reviewed efficacy, production scaling, or Art Optimizer's atlas algorithm.

## `MURDOCK-GR-CODE`

**Type:** Source code  
**Canonical citation:**

> Ryn Murdock. `generative_recommender`. GitHub repository. https://github.com/rynmurdock/generative_recommender

**Use for:** actual prototype workflow, CLIP image-feature anchoring, alternating least-squares-style implementation, FLICKR-AES data preparation, generation bridge.

## `MURDOCK-PP`

**Type:** Source code  
**Canonical citation:**

> Ryn Murdock. `preference-prior`. GitHub repository. https://github.com/rynmurdock/preference-prior

**Use for:** sequence of preferred media embeddings to held-out preferred embedding; adapted prior architecture; research-code scope.

## `HU-2008`

**Type:** Peer reviewed  
**Canonical citation:**

> Yifan Hu, Yehuda Koren, and Chris Volinsky. “Collaborative Filtering for Implicit Feedback Datasets.” In *2008 Eighth IEEE International Conference on Data Mining*, 263–272. IEEE, 2008. https://doi.org/10.1109/ICDM.2008.22

**Use for:** weighted latent-factor modeling of implicit feedback.

## `REN-2017`

**Type:** Peer reviewed  
**Canonical citation:**

> Jian Ren, Xiaohui Shen, Zhe Lin, Radomír Měch, and David J. Foran. “Personalized Image Aesthetics.” In *Proceedings of the IEEE International Conference on Computer Vision*, 638–647, 2017. https://openaccess.thecvf.com/content_ICCV_2017/html/Ren_Personalized_Image_Aesthetics_ICCV_2017_paper.html

**Use for:** FLICKR-AES and personalized aesthetic prediction from overlapping user ratings.

## `CLIP-2021`

**Type:** Peer reviewed  
**Canonical citation:**

> Alec Radford, Jong Wook Kim, Chris Hallacy, Aditya Ramesh, Gabriel Goh, Sandhini Agarwal, et al. “Learning Transferable Visual Models From Natural Language Supervision.” In *Proceedings of the 38th International Conference on Machine Learning*, PMLR 139:8748–8763, 2021. https://proceedings.mlr.press/v139/radford21a.html

**Use for:** joint image-language embedding representation.

## `GENEREC-2023`

**Type:** Preprint  
**Canonical citation:**

> Wenjie Wang, Xinyu Lin, Fuli Feng, Xiangnan He, and Tat-Seng Chua. “Generative Recommendation: Towards Next-generation Recommender Paradigm.” arXiv:2304.03516, 2023. https://arxiv.org/abs/2304.03516

**Use for:** broader generative-recommendation paradigm involving retrieval, editing, creation, user instructions, and fidelity checks.

## `ECLIPSE-2023`

**Type:** Preprint  
**Canonical citation:**

> Maitreya Patel, Changhoon Kim, Sheng Cheng, Chitta Baral, and Yezhou Yang. “ECLIPSE: A Resource-Efficient Text-to-Image Prior for Image Generations.” arXiv:2312.04655, 2023. https://arxiv.org/abs/2312.04655

**Use for:** the text-to-image prior architecture adapted by Murdock's preference-prior project.

# B. Interactive model-guided design

## `SHIMIZU-UIST-2020`

**Type:** Peer reviewed  
**Canonical citation:**

> Evan Shimizu, Matthew Fisher, Sylvain Paris, James McCann, and Kayvon Fatahalian. “Design Adjectives: A Framework for Interactive Model-Guided Exploration of Parameterized Design Spaces.” In *Proceedings of the 33rd Annual ACM Symposium on User Interface Software and Technology*, 261–278, 2020. https://doi.org/10.1145/3379337.3415866

**Use for:** framework, GPR-based subjective design modeling, gallery exploration, sampling modes, study and case-study evidence.

## `SHIMIZU-THESIS-2020`

**Type:** Thesis  
**Canonical citation:**

> Evan Shimizu. *Improving Parameterized Design with Interactive User-Guided Sampling and Parameter Identification Tools*. PhD thesis, Carnegie Mellon University, CMU-CS-20-104, 2020. https://csd.cs.cmu.edu/sites/default/files/phd-thesis/CMU-CS-20-104.pdf

**Use for:** equations, kernel details, guided rejection sampler, Towards/Away/Similar Score/Axis, UI figures, parameter tools, future mobile/large-screen designs, limitations.

## `SHIMIZU-CODE`

**Type:** Source code  
**Canonical citation:**

> Evan Shimizu. `DesignAdjectives`. GitHub repository. https://github.com/ebshimizu/DesignAdjectives

**Use for:** released system architecture and implementation dependencies.

## `SHIMIZU-PROJECT`

**Type:** Project page  
**Canonical citation:**

> Carnegie Mellon Graphics. “Design Adjectives.” https://graphics.cs.cmu.edu/projects/design-adjectives/

**Use for:** official abstract, video, code, paper and BibTeX links.

# C. Preference learning and Bayesian optimization

## `CHU-GHAHRAMANI-2005`

**Type:** Peer reviewed  
**Canonical citation:**

> Wei Chu and Zoubin Ghahramani. “Preference Learning with Gaussian Processes.” In *Proceedings of the 22nd International Conference on Machine Learning*, 137–144, 2005. https://doi.org/10.1145/1102351.1102369

**Use for:** GP latent-utility models from pairwise preferences.

## `BROCHU-APL-2007`

**Type:** Peer reviewed  
**Canonical citation:**

> Eric Brochu, Nando de Freitas, and Abhijeet Ghosh. “Active Preference Learning with Discrete Choice Data.” In *Advances in Neural Information Processing Systems 20*, 2007. https://papers.nips.cc/paper_files/paper/2007/hash/b6a1085a27ab7bff7550f8a3bd017df8-Abstract.html

**Use for:** active query selection from discrete choices and graphics/material examples.

## `BROCHU-ANIMATION-2010`

**Type:** Peer reviewed  
**Canonical citation:**

> Eric Brochu, Tyson Brochu, and Nando de Freitas. “A Bayesian Interactive Optimization Approach to Procedural Animation Design.” In *Proceedings of the 2010 ACM SIGGRAPH/Eurographics Symposium on Computer Animation*, 103–112, 2010. https://doi.org/10.2312/SCA/SCA10/103-112

**Use for:** human-in-the-loop Bayesian optimization of subjective graphics parameters.

## `PBO-2017`

**Type:** Peer reviewed  
**Canonical citation:**

> Javier González, Zhenwen Dai, Andreas Damianou, and Neil D. Lawrence. “Preferential Bayesian Optimization.” In *Proceedings of the 34th International Conference on Machine Learning*, PMLR 70:1282–1291, 2017. https://proceedings.mlr.press/v70/gonzalez17a.html

**Use for:** Bayesian optimization when observations are preferences rather than objective values.

## `SEQUENTIAL-GALLERY-2020`

**Type:** Peer reviewed  
**Canonical citation:**

> Yuki Koyama, Issei Sato, and Masataka Goto. “Sequential Gallery for Interactive Visual Design Optimization.” *ACM Transactions on Graphics* 39, no. 4, Article 88, 2020. https://doi.org/10.1145/3386569.3392444

**Use for:** visually answerable sequential optimization queries and gallery-based high-dimensional design search.

## `INCONSISTENT-GP-2022`

**Type:** Peer reviewed  
**Canonical citation:**

> Siu Lun Chau, Javier Gonzalez, and Dino Sejdinovic. “Learning Inconsistent Preferences with Gaussian Processes.” In *Proceedings of the 25th International Conference on Artificial Intelligence and Statistics*, PMLR 151, 2022. https://proceedings.mlr.press/v151/lun-chau22a.html

**Use for:** nontransitive/inconsistent preference modeling.

# D. Interactive evolutionary and generative search

## `TAKAGI-2001`

**Type:** Peer reviewed  
**Canonical citation:**

> Hideyuki Takagi. “Interactive Evolutionary Computation: Fusion of the Capabilities of EC Optimization and Human Evaluation.” *Proceedings of the IEEE* 89, no. 9: 1275–1296, 2001. https://doi.org/10.1109/5.949485

**Use for:** interactive evolutionary computation lineage and human-fatigue limitations.

## `SWIPEGANSPACE-2024`

**Type:** Preprint  
**Canonical citation:**

> Yuto Nakashima, Mingzhe Yang, and Yukino Baba. “SwipeGANSpace: Swipe-to-Compare Image Generation via Efficient Latent Space Exploration.” arXiv:2404.19693, 2024. https://arxiv.org/abs/2404.19693

**Use for:** swipe comparison, PCA StyleGAN subspaces, preferential BO, dimension bandit, preference changes through inspiration.

## `MULTIBO-2026`

**Type:** Preprint  
**Canonical citation:**

> Rajalaxmi Rajagopalan, Debottam Dutta, Yu-Lin Wei, and Romit Roy Choudhury. “Personalized Image Generation via Human-in-the-loop Bayesian Optimization.” arXiv:2602.02388, 2026. https://arxiv.org/abs/2602.02388

**Use for:** multi-choice PBO, constrained attention transformation space, implicit target alignment, user/baseline evaluation.

## `GIMMBO-2026`

**Type:** Preprint  
**Canonical citation:**

> Chenxi Liu, Selena Ling, and Alec Jacobson. “GimmBO: Interactive Generative Image Model Merging via Bayesian Optimization.” arXiv:2601.18585, 2026. https://arxiv.org/abs/2601.18585

**Use for:** preferential BO over sparse constrained adapter-mixture weights.

# E. Generator control directions and conditioning

## `GANSPACE-2020`

**Type:** Peer reviewed  
**Canonical citation:**

> Erik Härkönen, Aaron Hertzmann, Jaakko Lehtinen, and Sylvain Paris. “GANSpace: Discovering Interpretable GAN Controls.” In *Advances in Neural Information Processing Systems 33*, 2020. https://neurips.cc/virtual/2020/public/poster_6fe43269967adbb64ec6149852b5cc3e.html

**Use for:** PCA in latent/activation spaces and layer-wise interpretable GAN controls.

## `VOYNOV-BABENKO-2020`

**Type:** Peer reviewed  
**Canonical citation:**

> Andrey Voynov and Artem Babenko. “Unsupervised Discovery of Interpretable Directions in the GAN Latent Space.” In *Proceedings of the 37th International Conference on Machine Learning*, PMLR 119:9786–9796, 2020. https://proceedings.mlr.press/v119/voynov20a.html

**Use for:** unsupervised discovery of model-native interpretable GAN directions.

## `STYLECLIP-2021`

**Type:** Peer reviewed  
**Canonical citation:**

> Or Patashnik, Zongze Wu, Eli Shechtman, Daniel Cohen-Or, and Dani Lischinski. “StyleCLIP: Text-Driven Manipulation of StyleGAN Imagery.” In *Proceedings of the IEEE/CVF International Conference on Computer Vision*, 2085–2094, 2021. https://doi.org/10.1109/ICCV48922.2021.00209

**Use for:** CLIP-guided latent optimization, learned mappers, and input-agnostic StyleSpace directions with controllable strength.

## `FABRIC-2024`

**Type:** Peer-reviewed workshop proceedings  
**Canonical citation:**

> Dimitri von Rütte, Elisabetta Fedele, Jonathan Thomm, and Lukas Wolf. “FABRIC: Personalizing Diffusion Models with Iterative Feedback.” In *Computer Vision – ECCV 2024 Workshops*, LNCS 15642, 385–400. Springer, 2024. https://doi.org/10.1007/978-3-031-91907-7_23

**Use for:** training-free positive/negative feedback-image conditioning through diffusion self-attention.

# F. Offline generator adaptation

## `DRAFT-2023`

**Type:** Preprint  
**Canonical citation:**

> Kevin Clark, Paul Vicol, Kevin Swersky, and David J. Fleet. “Directly Fine-Tuning Diffusion Models on Differentiable Rewards.” arXiv:2309.17400, 2023. https://arxiv.org/abs/2309.17400

**Use for:** backpropagating differentiable rewards through diffusion sampling and efficient truncated variants.

## `DIFFUSION-DPO-2023`

**Type:** Preprint  
**Canonical citation:**

> Bram Wallace, Meihua Dang, Rafael Rafailov, Linqi Zhou, Aaron Lou, Senthil Purushwalkam, Stefano Ermon, Caiming Xiong, Shafiq Joty, and Nikhil Naik. “Diffusion Model Alignment Using Direct Preference Optimization.” arXiv:2311.12908, 2023. https://arxiv.org/abs/2311.12908

**Use for:** direct diffusion-model alignment from comparison data without a separately optimized RL reward loop.

# Selected BibTeX

```bibtex
@inproceedings{shimizu2020designadjectives,
  author    = {Shimizu, Evan and Fisher, Matthew and Paris, Sylvain and McCann, James and Fatahalian, Kayvon},
  title     = {Design Adjectives: A Framework for Interactive Model-Guided Exploration of Parameterized Design Spaces},
  booktitle = {Proceedings of the 33rd Annual ACM Symposium on User Interface Software and Technology},
  pages     = {261--278},
  year      = {2020},
  doi       = {10.1145/3379337.3415866}
}

@phdthesis{shimizu2020thesis,
  author = {Shimizu, Evan},
  title  = {Improving Parameterized Design with Interactive User-Guided Sampling and Parameter Identification Tools},
  school = {Carnegie Mellon University},
  number = {CMU-CS-20-104},
  year   = {2020}
}

@inproceedings{chu2005preference,
  author    = {Chu, Wei and Ghahramani, Zoubin},
  title     = {Preference Learning with Gaussian Processes},
  booktitle = {Proceedings of the 22nd International Conference on Machine Learning},
  pages     = {137--144},
  year      = {2005},
  doi       = {10.1145/1102351.1102369}
}

@inproceedings{gonzalez2017preferential,
  author    = {Gonzalez, Javier and Dai, Zhenwen and Damianou, Andreas and Lawrence, Neil D.},
  title     = {Preferential Bayesian Optimization},
  booktitle = {Proceedings of the 34th International Conference on Machine Learning},
  series    = {Proceedings of Machine Learning Research},
  volume    = {70},
  pages     = {1282--1291},
  year      = {2017}
}

@article{koyama2020sequential,
  author  = {Koyama, Yuki and Sato, Issei and Goto, Masataka},
  title   = {Sequential Gallery for Interactive Visual Design Optimization},
  journal = {ACM Transactions on Graphics},
  volume  = {39},
  number  = {4},
  year    = {2020},
  doi     = {10.1145/3386569.3392444}
}

@article{takagi2001interactive,
  author  = {Takagi, Hideyuki},
  title   = {Interactive Evolutionary Computation: Fusion of the Capabilities of EC Optimization and Human Evaluation},
  journal = {Proceedings of the IEEE},
  volume  = {89},
  number  = {9},
  pages   = {1275--1296},
  year    = {2001},
  doi     = {10.1109/5.949485}
}

@inproceedings{voynov2020directions,
  author    = {Voynov, Andrey and Babenko, Artem},
  title     = {Unsupervised Discovery of Interpretable Directions in the GAN Latent Space},
  booktitle = {Proceedings of the 37th International Conference on Machine Learning},
  series    = {Proceedings of Machine Learning Research},
  volume    = {119},
  pages     = {9786--9796},
  year      = {2020}
}

@inproceedings{patashnik2021styleclip,
  author    = {Patashnik, Or and Wu, Zongze and Shechtman, Eli and Cohen-Or, Daniel and Lischinski, Dani},
  title     = {StyleCLIP: Text-Driven Manipulation of StyleGAN Imagery},
  booktitle = {Proceedings of the IEEE/CVF International Conference on Computer Vision},
  pages     = {2085--2094},
  year      = {2021},
  doi       = {10.1109/ICCV48922.2021.00209}
}

@inproceedings{rutte2024fabric,
  author    = {von Rutte, Dimitri and Fedele, Elisabetta and Thomm, Jonathan and Wolf, Lukas},
  title     = {FABRIC: Personalizing Diffusion Models with Iterative Feedback},
  booktitle = {Computer Vision -- ECCV 2024 Workshops},
  pages     = {385--400},
  year      = {2024},
  doi       = {10.1007/978-3-031-91907-7_23}
}
```

## Maintenance rule

When a preprint receives a peer-reviewed publication:

1. add the archival citation;
2. retain the arXiv link for open access if useful;
3. update source type;
4. check whether title/authors changed;
5. update every review that makes a venue-sensitive claim.

A citation ledger is useful only if it is maintained as research status changes.
