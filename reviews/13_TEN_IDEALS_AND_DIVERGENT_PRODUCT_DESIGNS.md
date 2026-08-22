# Ten Ideals and Divergent Product Designs

**Status:** future UI, action, UX, and data-model design space  
**Tracking issue:** [#10](https://github.com/nbardy/art-optimizer/issues/10)

The project should not build one interface containing every possible control. The following ten ideals are expressed as divergent product families. They may share model infrastructure and immutable event facts, but they intentionally differ in actions, rendering policy, learned state, and user expectations.

## Summary table

| # | Ideal | Divergent product family | Primary promise |
|---:|---|---|---|
| 1 | Statistical truth | Truthful Search Canvas | every command means exactly what it trains |
| 2 | Real inheritance | Evolution Studio | selected image visibly parents descendants |
| 3 | Stochastic agency | Realization Browser | explore another seed without changing taste |
| 4 | Inspectable intent | Design Adjective Workbench | create and sweep subjective learned axes |
| 5 | Recurring evidence | Concept Garden | concepts emerge from repeated visual patterns |
| 6 | Multimodal memory | Taste Atlas Explorer | navigate several persistent preference modes |
| 7 | Compositional authorship | Concept Composer | combine mature concepts into new worlds |
| 8 | Answerable comparisons | Counterfactual Lab | isolate exactly what one choice teaches |
| 9 | Multi-anchor creativity | Branch Forest | keep several promising designs alive at once |
| 10 | Policy-level experiments | Research Harness | compare genuinely different creative systems |

## Ideal 1: commands must tell the statistical truth

### Divergent design: Truthful Search Canvas

This is the rigorous successor to the current baseline.

### UI

One committed image, a small candidate gallery, and explicit commands:

```text
Choose
More variety
None of these
Broken render
Favorite
New region
```

### Actions

- **Choose:** one discrete-choice observation.
- **More variety:** no preference update; change novelty/seed policy.
- **None of these:** weak anchor-wins observation.
- **Broken render:** exclude candidate, zero preference effect.
- **New region:** broad control-space move, explicitly not a dislike.

### UX ideal

The user should be able to predict what the model learns from every button.

### Data model

```text
CommandFact
PreferenceObservation
NoveltyRequest
RenderQualityReport
```

The raw command remains immutable. Learner projections may change later without rewriting history.

### Divergent hypothesis

A smaller but truthful action vocabulary will create more trust and cleaner preference data than an apparently simpler overloaded reroll button.

## Ideal 2: a selected image should be a real generative parent when the UI says “evolve”

### Divergent design: Evolution Studio

### UI

A full-canvas image with four visible descendants and preservation locks:

```text
keep subject
keep composition
keep palette
keep texture
edit amount
```

The user chooses a descendant or adjusts one preservation profile.

### Actions

- evolve locally;
- strengthen/weaken mutation;
- lock/unlock a property;
- branch;
- compare with parent;
- undo.

### UX ideal

A detail selected in one generation should not disappear merely because the next render is a fresh text-to-image sample.

### Data model

```text
DesignState
    navigation_parent_id
    generative_parent_id
    inversion/latent reference
    preservation profile
    edit strength
    seed/noise provenance
```

Navigation ancestry and generative ancestry are separate.

### Divergent hypothesis

Parent-conditioned rendering will better match intuitive “evolution” expectations, even if it sacrifices some experimental control and global novelty.

## Ideal 3: stochastic variation should be a first-class creative action

### Divergent design: Realization Browser

### UI

The current concept/action composition stays fixed while the user browses realizations:

```text
same composition, another realization
nearby realization
wild realization
return to semantic editing
```

### Actions

- exact same root refinement;
- correlated-noise variation;
- fresh-seed variation;
- pin a realization;
- compare two roots under one action.

### UX ideal

The user can ask for novelty without changing or criticizing the learned semantic direction.

### Data model

```text
NoiseState
NoiseRelation
SemanticActionState
RealizationFamily
```

An image belongs to both a semantic composition and a stochastic family.

### Divergent hypothesis

Many “I want more options” requests are primarily stochastic, not preference-learning requests.

## Ideal 4: learned intent should be inspectable and sweepable

### Divergent design: Design Adjective Workbench

Inspired most directly by Shimizu's Design Adjectives.

### UI

The user creates an adjective through examples, then receives:

```text
Towards
Away
Similar score
Axis sweep
Affected controls
```

A five-image axis view shows calibrated amounts around a design.

### Actions

- rate/select examples for one adjective;
- inspect uncertainty;
- sweep amount;
- rename adjective;
- freeze or retrain;
- apply to another compatible world.

### UX ideal

The system should expose what it thinks the learned property is doing rather than hiding all optimization behind candidate selection.

### Data model

```text
DesignAdjective
    training examples
    subjective-function snapshot
    uncertainty
    affected parameter/control basis
    validity region
    axis calibration
```

### Divergent hypothesis

Explicit creation of a few inspectable subjective functions may outperform silent accumulation of many opaque lanes.

## Ideal 5: concepts should require recurring visual evidence

### Divergent design: Concept Garden

### UI

Concepts appear first as provisional sprouts. They mature only after repeated evidence.

```text
provisional
supported
active
dormant
conflicted
```

Each concept displays multiple exemplars and counterexamples.

### Actions

- confirm provisional concept;
- merge two concepts;
- split one concept;
- add/remove exemplar;
- mark counterexample;
- force active/dormant;
- inspect where it works.

### UX ideal

One selected image is an example, not an attribute.

### Data model

```text
ConceptObservation
ConceptComponent
ConceptMembership
ConceptExemplar
ConceptCounterexample
ConceptLifecycleEvent
ConceptActionHead per control basis
```

### Divergent hypothesis

A slower concept lifecycle will produce fewer but more reusable and understandable concepts than immediate singleton activation.

## Ideal 6: persistent taste should be multimodal, not one average

### Divergent design: Taste Atlas Explorer

Inspired by Murdock's interaction-conditioned generative preference representation, extended to multiple coherent modes.

### UI

A map or set of taste regions:

```text
active mode
another side of my taste
combine two modes
outside my known taste
surprise me
```

The user explores examples from a mode without manipulating raw controls.

### Actions

- open mode;
- favorite/export into mode;
- split/merge modes;
- combine modes;
- mark mode dormant;
- explore outside-prior space.

### UX ideal

The system remembers different aesthetics separately rather than averaging them into one compromise.

### Data model

```text
PreferenceMode
MediaEvidenceSequence
VisualDistribution
ContextDistribution
GenerationAdapter/reference set
ModeRelation
```

### Divergent hypothesis

Persistent multimodal media history will guide new worlds better than centroids of action coordinates.

## Ideal 7: mature concepts should be composable without forcing constant manual control

### Divergent design: Concept Composer

### UI

A small number of mature concept cards can be placed into a composition tray. Each card has amount and optional preservation scope.

```text
include
exclude
amount
lock
recast
```

The system previews interaction warnings when two concepts conflict.

### Actions

- add/remove concept;
- change amount;
- choose a context/subject;
- recast with another stochastic root;
- save composition as a reusable recipe.

### UX ideal

Composition should feel like arranging reusable artistic ingredients, not editing a growing list of one-off selections.

### Data model

```text
ConceptRecipe
RecipeTerm
CompatibilityEstimate
ConflictReceipt
ModelSpecificTransport
RecastResult
```

The recipe is model-neutral where possible; each model/control basis has a transport head with uncertainty.

### Divergent hypothesis

Explicit composition becomes useful only after concept quality is high; before then it amplifies noise and false semantics.

## Ideal 8: each comparison should be answerable

### Divergent design: Counterfactual Lab

### UI

Instead of always showing four unrelated points, the system sometimes shows controlled comparisons:

```text
same action, two seeds
same seed, two actions
one concept at two amounts
current design versus equal-score alternative
```

### Actions

- choose A/B;
- both;
- neither;
- cannot judge because render is broken;
- property changed but quality did not;
- quality changed but property did not.

### UX ideal

The user should be able to understand what question the system is asking and answer it without reverse-engineering four images.

### Data model

```text
ExperimentQuestion
ControlledFactors
HeldConstantFactors
ResponseType
InformationGainReceipt
```

### Divergent hypothesis

Fewer, more diagnostic comparisons may learn faster and produce less fatigue than perpetual four-way slates.

## Ideal 9: creativity should not require one active anchor

### Divergent design: Branch Forest

### UI

Several live anchors remain visible:

```text
main branch
wild branch
concept-composition branch
alternate taste branch
```

Each can receive candidates independently. The user may cross two branches or archive one.

### Actions

- keep branch alive;
- pause/archive;
- fork;
- compare branches;
- cross/combine;
- promote to main;
- return to branch-specific history.

### UX ideal

Creative exploration is often plural. A single current image forces premature convergence and discards promising alternatives.

### Data model

```text
BranchWorkspace
ActiveAnchorSet
BranchSpecificPosterior
SharedPreferenceFacts
CrossOperation
BranchBudget
```

### Divergent hypothesis

Maintaining 2–4 active anchors will increase discovery and reduce regret, at the cost of more state and possible cognitive load.

## Ideal 10: UI experiments must own genuinely different policies

### Divergent design: Research Harness

### UI

A treatment selector clearly states the hypothesis being tested. Switching treatment may create a new projection or session fork rather than silently reusing incompatible derived state.

### Experiment policy

```text
renderer mode
candidate count
candidate-generation policy
seed/noise policy
command semantics
preference learner
concept learner
concept promotion threshold
concept visibility/editability
metrics
```

### Actions

The available actions are policy-dependent. A true-evolution treatment may expose preservation locks; a search treatment may expose axis sweeps; a realization treatment may expose seed variation.

### UX ideal

Different interfaces should not merely rearrange the same controls. Each should test a coherent product thesis.

### Data model

```text
ExperimentPolicy
ExperimentAssignment
ImmutableSharedFact
PolicyProjection
PolicyLearnerSnapshot
TreatmentMetric
CrossTreatmentComparison
```

### Divergent hypothesis

The project will learn faster by comparing a few internally coherent systems than by adding every idea to one universal interface.

## Principles shared by all ten designs

Even divergent products should share these invariants:

1. raw user actions are immutable facts;
2. commands expose their preference effect;
3. failed renders create no aesthetic label;
4. generated designs carry complete provenance;
5. learned concepts and preference modes carry evidence and uncertainty;
6. model/control-basis scope is explicit;
7. history and undo remain reliable;
8. visual-output metrics supplement action-space metrics;
9. the user can correct durable learned state;
10. claims are limited to measured behavior.

## Recommended first three treatments

Do not implement all ten.

### Treatment A — Truthful Search Canvas

Lowest risk. Split shuffle from none-of-these, add hybrid seeds, add perceptual slate reranking, and relabel the product as generative-space search.

### Treatment B — Evolution Studio

Highest product-value uncertainty. Add parent-conditioned rendering and preservation controls. Compare descendant continuity against Treatment A.

### Treatment C — Concept Garden + Recast

Add server-side provisional concept evidence with visual deltas. Expose only mature concepts and test whether they survive fresh stochastic roots.

These three treatments cover the major unresolved product question without building a cockpit containing every possible action.
