# Use Case Diagram

Onderstaand diagram toont de belangrijkste interacties met de Expertum AI Support Assistant.

```plantuml
@startuml
left to right direction

actor "Klant" as Customer
actor "Supportmedewerker" as Agent
actor "Student/Ontwikkelaar" as Developer

rectangle "Expertum AI Support Assistant" {
  usecase "Klantvraag stellen" as UC_Ask
  usecase "Antwoord ontvangen" as UC_Answer
  usecase "Help topics raadplegen" as UC_Help

  usecase "Relevante tickets ophalen" as UC_Tickets
  usecase "Producthandleiding raadplegen" as UC_Manuals
  usecase "Antwoord genereren met LLM" as UC_Generate

  usecase "Gebruikte bronnen bekijken" as UC_Sources
  usecase "Supportticket indexeren" as UC_IndexTickets
  usecase "Producthandleiding indexeren" as UC_IndexManuals
  usecase "RAG-varianten evalueren" as UC_Evaluate
}

Customer --> UC_Ask
Customer --> UC_Answer
Customer --> UC_Help

UC_Ask .> UC_Tickets : <<include>>
UC_Ask .> UC_Manuals : <<include>>
UC_Tickets .> UC_Generate : <<include>>
UC_Manuals .> UC_Generate : <<include>>
UC_Generate .> UC_Answer : <<include>>

Agent --> UC_Sources
Agent --> UC_Answer

Developer --> UC_IndexTickets
Developer --> UC_IndexManuals
Developer --> UC_Evaluate

UC_IndexTickets .> UC_Tickets : <<include>>
UC_IndexManuals .> UC_Manuals : <<include>>

@enduml
```

## Korte uitleg

De klant gebruikt de applicatie om een supportvraag te stellen en een antwoord te ontvangen. De AI-assistent zoekt daarbij relevante informatie op uit twee kennisbronnen: historische supporttickets en producthandleidingen. Daarna genereert het lokale LLM een klantgericht antwoord.

De supportmedewerker of demonstrator kan de gebruikte bronnen bekijken om te controleren waarop het antwoord gebaseerd is. De student of ontwikkelaar beheert de technische kant van de proof-of-concept: tickets indexeren, handleidingen indexeren en evaluatietesten uitvoeren met verschillende RAG-varianten.

## Actoren

- **Klant**: stelt een vraag en ontvangt een antwoord.
- **Supportmedewerker**: bekijkt het gegenereerde antwoord en de opgehaalde bronnen.
- **Student/Ontwikkelaar**: bouwt en onderhoudt de indexen en voert evaluaties uit.

## Belangrijkste use cases

- **Klantvraag stellen**: de klant voert een vraag in via de webinterface.
- **Relevante tickets ophalen**: het systeem zoekt historische tickets met Chroma en LangChain.
- **Producthandleiding raadplegen**: bij technische vragen zoekt het systeem ook in producthandleidingen.
- **Antwoord genereren met LLM**: LLaMA 3.1 8B genereert een antwoord op basis van de opgehaalde context.
- **Gebruikte bronnen bekijken**: de gebruiker kan controleren welke tickets of handleidingfragmenten gebruikt werden.
- **RAG-varianten evalueren**: de student vergelijkt antwoorden met alleen tickets, alleen handleidingen en de hybride aanpak.

