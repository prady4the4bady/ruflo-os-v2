import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { LumynConsole } from "../apps/LumynConsole";

describe("LumynConsole", () => {
  it("renders the tab bar", () => {
    render(<LumynConsole />);
    // Use role-based query to avoid matching "skills" in body text
    expect(screen.getByRole("button", { name: /Skills/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Acquire/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /SOUL/i })).toBeInTheDocument();
  });

  it("shows skills table after loading", async () => {
    render(<LumynConsole />);
    await waitFor(() =>
      expect(screen.getByText("test_skill")).toBeInTheDocument()
    );
    expect(screen.getByText("active")).toBeInTheDocument();
  });

  it("shows elite star for elite skills", async () => {
    render(<LumynConsole />);
    await waitFor(() => expect(screen.getByText("test_skill")).toBeInTheDocument());
    // Elite column should not show star for our non-elite fixture
    expect(screen.queryAllByTitle("Elite").length).toBe(0);
  });

  it("switches to Acquire tab", async () => {
    render(<LumynConsole />);
    const acquireTab = screen.getByText(/Acquire/i);
    fireEvent.click(acquireTab);
    await waitFor(() =>
      expect(screen.getByPlaceholderText(/Describe the task/i)).toBeInTheDocument()
    );
  });

  it("acquire skill submits and shows result", async () => {
    render(<LumynConsole />);
    fireEvent.click(screen.getByText(/Acquire/i));

    const textarea = await screen.findByPlaceholderText(/Describe the task/i);
    fireEvent.change(textarea, { target: { value: "Sort a list" } });

    const button = screen.getByText("Acquire Skill");
    fireEvent.click(button);

    await waitFor(() =>
      expect(screen.getByText("Skill acquired!")).toBeInTheDocument()
    );
    expect(screen.getByText("acquired_skill")).toBeInTheDocument();
  });

  it("acquire button is disabled when textarea is empty", () => {
    render(<LumynConsole />);
    fireEvent.click(screen.getByText(/Acquire/i));
    const button = screen.getByText("Acquire Skill");
    expect(button).toBeDisabled();
  });

  it("switches to SOUL tab and loads profile", async () => {
    render(<LumynConsole />);
    fireEvent.click(screen.getByText(/SOUL/i));
    await waitFor(() => expect(screen.getByText(/SOUL.md/i)).toBeInTheDocument());
    // Name field should be pre-filled
    const nameInput = screen.getAllByDisplayValue("Kryos User");
    expect(nameInput.length).toBeGreaterThan(0);
  });

  it("save soul button disabled when not dirty", async () => {
    render(<LumynConsole />);
    fireEvent.click(screen.getByText(/SOUL/i));
    const saveBtn = await screen.findByText("Save SOUL");
    expect(saveBtn).toBeDisabled();
  });

  it("save soul button enabled after editing a field", async () => {
    render(<LumynConsole />);
    fireEvent.click(screen.getByText(/SOUL/i));
    const nameInputs = await screen.findAllByDisplayValue("Kryos User");
    fireEvent.change(nameInputs[0], { target: { value: "New Name" } });
    const saveBtn = screen.getByText("Save SOUL");
    expect(saveBtn).not.toBeDisabled();
  });
});
