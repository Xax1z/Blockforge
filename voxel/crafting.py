"""
Advanced crafting system for voxel game.
Handles crafting recipes, inventory management, and crafting logic.
"""

from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict
from direct.gui.DirectGui import DirectFrame, DirectLabel, DirectButton, DGG
from panda3d.core import TextNode

# Import block constants
from .chunk import (
    BLOCK_AIR,
    BLOCK_GRASS,
    BLOCK_DIRT,
    BLOCK_STONE,
    BLOCK_BEDROCK,
    BLOCK_SAND,
    BLOCK_WOOD,
    BLOCK_LEAVES,
    BLOCK_COBBLESTONE,
    BLOCK_BRICK,
    BLOCK_SANDSTONE,
    BLOCK_CACTUS,
    BLOCK_PLANKS,
    BLOCK_STICKS,
    BLOCK_PICKAXE_WOOD,
    BLOCK_PICKAXE_STONE,
    BLOCK_PICKAXE_IRON,
    BLOCK_AXE_WOOD,
    BLOCK_AXE_STONE,
    BLOCK_AXE_IRON,
    BLOCK_SWORD_WOOD,
    BLOCK_SWORD_STONE,
    BLOCK_SWORD_IRON,
    BLOCK_SHOVEL_WOOD,
    BLOCK_SHOVEL_STONE,
    BLOCK_SHOVEL_IRON,
    BLOCK_CRAFTING_TABLE,
    BLOCK_FURNACE,
    BLOCK_CHEST,
    BLOCK_IRON_INGOT,
    BLOCK_JUNGLE_LOG,
    BLOCK_BIRCH_LOG,
    BLOCK_JUNGLE_PLANKS,
    BLOCK_BIRCH_PLANKS,
)

# Crafting recipes - each recipe defines ingredients and output
# Format: {ingredient_block_id: count} -> (output_block_id, output_count, requires_3x3=False)
# requires_3x3 = True means it needs a crafting table (3x3 grid)
# requires_3x3 = False means it can be made in inventory (2x2 grid)
CRAFTING_RECIPES = [
    # Basic blocks (2x2 recipes)
    ({BLOCK_WOOD: 1}, (BLOCK_PLANKS, 4, False)),  # Wood -> Planks
    ({BLOCK_JUNGLE_LOG: 1}, (BLOCK_JUNGLE_PLANKS, 4, False)), # Jungle Log -> Jungle Planks
    ({BLOCK_BIRCH_LOG: 1}, (BLOCK_BIRCH_PLANKS, 4, False)), # Birch Log -> Birch Planks

    ({BLOCK_PLANKS: 2}, (BLOCK_STICKS, 4, False)),  # Planks -> Sticks
    ({BLOCK_JUNGLE_PLANKS: 2}, (BLOCK_STICKS, 4, False)), # Jungle Planks -> Sticks
    ({BLOCK_BIRCH_PLANKS: 2}, (BLOCK_STICKS, 4, False)), # Birch Planks -> Sticks

    ({BLOCK_PLANKS: 4}, (BLOCK_CRAFTING_TABLE, 1, False)),  # Crafting table (2x2)
    ({BLOCK_JUNGLE_PLANKS: 4}, (BLOCK_CRAFTING_TABLE, 1, False)),
    ({BLOCK_BIRCH_PLANKS: 4}, (BLOCK_CRAFTING_TABLE, 1, False)),

    # Tools - Wood (3x3 recipes - need crafting table)
    ({BLOCK_PLANKS: 3, BLOCK_STICKS: 2}, (BLOCK_PICKAXE_WOOD, 1, True)),
    ({BLOCK_JUNGLE_PLANKS: 3, BLOCK_STICKS: 2}, (BLOCK_PICKAXE_WOOD, 1, True)),
    ({BLOCK_BIRCH_PLANKS: 3, BLOCK_STICKS: 2}, (BLOCK_PICKAXE_WOOD, 1, True)),

    ({BLOCK_PLANKS: 3, BLOCK_STICKS: 2}, (BLOCK_AXE_WOOD, 1, True)),
    ({BLOCK_JUNGLE_PLANKS: 3, BLOCK_STICKS: 2}, (BLOCK_AXE_WOOD, 1, True)),
    ({BLOCK_BIRCH_PLANKS: 3, BLOCK_STICKS: 2}, (BLOCK_AXE_WOOD, 1, True)),

    ({BLOCK_PLANKS: 1, BLOCK_STICKS: 2}, (BLOCK_SHOVEL_WOOD, 1, True)),
    ({BLOCK_JUNGLE_PLANKS: 1, BLOCK_STICKS: 2}, (BLOCK_SHOVEL_WOOD, 1, True)),
    ({BLOCK_BIRCH_PLANKS: 1, BLOCK_STICKS: 2}, (BLOCK_SHOVEL_WOOD, 1, True)),

    ({BLOCK_PLANKS: 2, BLOCK_STICKS: 1}, (BLOCK_SWORD_WOOD, 1, True)),
    ({BLOCK_JUNGLE_PLANKS: 2, BLOCK_STICKS: 1}, (BLOCK_SWORD_WOOD, 1, True)),
    ({BLOCK_BIRCH_PLANKS: 2, BLOCK_STICKS: 1}, (BLOCK_SWORD_WOOD, 1, True)),

    # Tools - Stone (3x3 recipes - need crafting table)
    ({BLOCK_COBBLESTONE: 3, BLOCK_STICKS: 2}, (BLOCK_PICKAXE_STONE, 1, True)),
    ({BLOCK_COBBLESTONE: 3, BLOCK_STICKS: 2}, (BLOCK_AXE_STONE, 1, True)),
    ({BLOCK_COBBLESTONE: 1, BLOCK_STICKS: 2}, (BLOCK_SHOVEL_STONE, 1, True)),
    ({BLOCK_COBBLESTONE: 2, BLOCK_STICKS: 1}, (BLOCK_SWORD_STONE, 1, True)),

    # Tools - Iron (3x3 recipes - need crafting table)
    ({BLOCK_IRON_INGOT: 3, BLOCK_STICKS: 2}, (BLOCK_PICKAXE_IRON, 1, True)),
    ({BLOCK_IRON_INGOT: 3, BLOCK_STICKS: 2}, (BLOCK_AXE_IRON, 1, True)),
    ({BLOCK_IRON_INGOT: 1, BLOCK_STICKS: 2}, (BLOCK_SHOVEL_IRON, 1, True)),
    ({BLOCK_IRON_INGOT: 2, BLOCK_STICKS: 1}, (BLOCK_SWORD_IRON, 1, True)),

    # Advanced crafting (requires 3x3 crafting table)
    ({BLOCK_COBBLESTONE: 8}, (BLOCK_FURNACE, 1, True)),  # Furnace
    ({BLOCK_PLANKS: 8}, (BLOCK_CHEST, 1, True)),  # Chest
    ({BLOCK_JUNGLE_PLANKS: 8}, (BLOCK_CHEST, 1, True)),
    ({BLOCK_BIRCH_PLANKS: 8}, (BLOCK_CHEST, 1, True)),
]


class CraftingSystem:
    """
    Advanced crafting system with recipe management and validation.
    """

    def __init__(self):
        self.recipes = self._load_recipes()
        self.recipes_2x2 = [r for r in self.recipes if not r['requires_3x3']]
        self.recipes_3x3 = [r for r in self.recipes if r['requires_3x3']]

    def _load_recipes(self) -> List[Dict[str, Any]]:
        """
        Convert raw recipe definitions into usable format.
        """
        recipes = []
        for ingredients, (output_id, output_count, requires_3x3) in CRAFTING_RECIPES:
            recipes.append({
                'ingredients': ingredients,
                'output': {'block': output_id, 'count': output_count},
                'requires_3x3': requires_3x3
            })
        return recipes

    def get_available_recipes(self, inventory: List[Optional[Dict[str, int]]], is_3x3_grid: bool = False) -> List[Dict[str, Any]]:
        """
        Return list of craftable recipes based on available inventory.

        Args:
            inventory: List of inventory slots [{'block': id, 'count': count} or None]
            is_3x3_grid: Whether using 3x3 crafting table (True) or 2x2 inventory (False)

        Returns:
            List of recipe dictionaries that can be crafted
        """
        available_recipes = []
        inventory_counts = self._count_inventory_items(inventory)

        # Select appropriate recipe set
        recipe_list = self.recipes if is_3x3_grid else self.recipes_2x2

        for recipe in recipe_list:
            # Check if we have enough of each ingredient
            can_craft = True
            for ingredient_id, required_count in recipe['ingredients'].items():
                available_count = inventory_counts.get(ingredient_id, 0)
                if available_count < required_count:
                    can_craft = False
                    break

            if can_craft:
                available_recipes.append(recipe)

        return available_recipes

    def can_craft_recipe(self, recipe: Dict[str, Any], inventory: List[Optional[Dict[str, int]]]) -> bool:
        """
        Check if a specific recipe can be crafted with current inventory.
        """
        inventory_counts = self._count_inventory_items(inventory)

        for ingredient_id, required_count in recipe['ingredients'].items():
            available_count = inventory_counts.get(ingredient_id, 0)
            if available_count < required_count:
                return False

        return True

    def craft_recipe(self, recipe: Dict[str, Any], inventory: List[Optional[Dict[str, int]]]) -> bool:
        """
        Attempt to craft a recipe, modifying the inventory.

        Args:
            recipe: Recipe dictionary
            inventory: Inventory to modify in-place

        Returns:
            True if crafting succeeded, False otherwise
        """
        if not self.can_craft_recipe(recipe, inventory):
            return False

        # Consume ingredients
        for ingredient_id, required_count in recipe['ingredients'].items():
            consumed = 0
            for slot in inventory:
                if slot is not None and slot['block'] == ingredient_id and consumed < required_count:
                    remaining = required_count - consumed
                    if slot['count'] <= remaining:
                        consumed += slot['count']
                        slot['count'] = 0
                        slot = None
                    else:
                        slot['count'] -= remaining
                        consumed += remaining
                        break

        # Add output to inventory
        output = recipe['output']
        self._add_to_inventory(inventory, output['block'], output['count'])

        return True

    def _count_inventory_items(self, inventory: List[Optional[Dict[str, int]]]) -> Dict[int, int]:
        """
        Count total items in inventory by block ID.
        """
        counts = defaultdict(int)
        for slot in inventory:
            if slot is not None:
                counts[slot['block']] += slot['count']
        return dict(counts)

    def _add_to_inventory(self, inventory: List[Optional[Dict[str, int]]], block_id: int, count: int) -> None:
        """
        Add items to inventory, stacking where possible.
        """
        # First, try to stack onto existing slots
        for slot in inventory:
            if slot is not None and slot['block'] == block_id:
                slot['count'] += count
                return

        # If no existing slot, find empty slot
        for i, slot in enumerate(inventory):
            if slot is None:
                inventory[i] = {'block': block_id, 'count': count}
                return

        # If inventory is full, drop items (could show a message instead)
        print(f"Inventory full, couldn't add {count} of block {block_id}")

    def get_recipe_by_output(self, output_block_id: int) -> Optional[Dict[str, Any]]:
        """
        Find a recipe that produces the given block ID.
        Returns the first matching recipe, or None if not found.
        """
        for recipe in self.recipes:
            if recipe['output']['block'] == output_block_id:
                return recipe
        return None

    def get_crafting_categories(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Organize recipes into categories for UI display.
        """
        categories = {
            'Basic': [],
            'Tools': [],
            'Blocks': [],
            'Advanced': []
        }

        # Import additional constants if needed for categorization
        # These could be moved to a separate constants file
        tool_blocks = {
            BLOCK_PICKAXE_WOOD, BLOCK_PICKAXE_STONE, BLOCK_PICKAXE_IRON,
            BLOCK_AXE_WOOD, BLOCK_AXE_STONE, BLOCK_AXE_IRON,
            BLOCK_SHOVEL_WOOD, BLOCK_SHOVEL_STONE, BLOCK_SHOVEL_IRON,
            BLOCK_SWORD_WOOD, BLOCK_SWORD_STONE, BLOCK_SWORD_IRON
        }

        advanced_blocks = {
            BLOCK_CRAFTING_TABLE, BLOCK_FURNACE, BLOCK_CHEST
        }

        for recipe in self.recipes:
            output_id = recipe['output']['block']

            if output_id in tool_blocks:
                categories['Tools'].append(recipe)
            elif recipe['requires_advanced'] or output_id in advanced_blocks:
                categories['Advanced'].append(recipe)
            elif recipe['requires_advanced'] is False:
                categories['Basic'].append(recipe)
            else:
                categories['Blocks'].append(recipe)

        return categories

class CraftingMenu:
    """Handles the crafting menu UI."""

    def __init__(self, app):
        self.app = app
        self.crafting_system = crafting_system
        self.menu_frame = None
        self.recipe_buttons = []
        self.current_hotbar = []
        self.has_advanced_station = False
        self.is_open = False

    def show_menu(self, available_recipes, hotbar, has_advanced_station):
        """Show the crafting menu with available recipes."""
        # If already open, don't create duplicates
        if self.is_open:
            return
            
        self.current_hotbar = hotbar
        self.has_advanced_station = has_advanced_station

        # Create menu background
        self.menu_frame = DirectFrame(
            frameColor=(0.1, 0.1, 0.1, 0.9),
            frameSize=(-0.8, 0.8, -0.7, 0.7),
            parent=self.app.aspect2d
        )

        # Title
        DirectLabel(
            text="Crafting Recipes",
            scale=0.08,
            pos=(0, 0, 0.6),
            text_fg=(1, 1, 1, 1),
            frameColor=(0, 0, 0, 0),
            parent=self.menu_frame
        )

        # Close instructions
        DirectLabel(
            text="Press C or Esc to close menu",
            scale=0.04,
            pos=(0, 0, -0.55),
            text_fg=(0.8, 0.8, 0.8, 1),
            frameColor=(0, 0, 0, 0),
            parent=self.menu_frame
        )

        # Create recipe buttons
        self._create_recipe_buttons(available_recipes)

        # Show menu and unlock mouse
        self.menu_frame.show()
        self.app.mouse_locked = False
        self.app._apply_mouse_lock()
        
        # NOW set is_open to True AFTER unlocking the mouse
        self.is_open = True

        # Hide other UI elements
        if self.app.hotbar_ui:
            self.app.hotbar_ui.hide()
        if self.app.crosshair:
            self.app.crosshair.hide()

        # Remove old escape binding and bind to close menu
        self.app.ignore("escape")
        self.app.accept("escape", self.hide_menu)

    def hide_menu(self):
        """Hide the crafting menu and restore game state."""
        if not self.is_open:
            return
            
        self.is_open = False

        if self.menu_frame:
            self.menu_frame.destroy()
            self.menu_frame = None

        self.recipe_buttons = []

        # Restore game UI
        self.app.mouse_locked = True
        self.app._apply_mouse_lock()

        if self.app.hotbar_ui:
            self.app.hotbar_ui.show()
        if self.app.crosshair:
            self.app.crosshair.show()

        # Re-bind escape to pause menu
        self.app.ignore("escape")
        self.app.accept("escape", self.app._toggle_pause_menu)

    def _create_recipe_buttons(self, available_recipes):
        """Create buttons for each available recipe."""
        button_height = 0.1
        start_y = 0.4
        y_spacing = -0.12

        for i, recipe in enumerate(available_recipes):
            y_pos = start_y + i * y_spacing

            # Create button frame
            button_frame = DirectFrame(
                frameColor=(0.3, 0.3, 0.3, 0.8),
                frameSize=(-0.7, 0.7, -button_height/2, button_height/2),
                pos=(0, 0, y_pos),
                parent=self.menu_frame
            )

            # Recipe text
            recipe_text = self._get_recipe_description(recipe)
            DirectLabel(
                text=recipe_text,
                scale=0.045,
                pos=(-0.6, 0, 0),
                text_fg=(1, 1, 1, 1),
                frameColor=(0, 0, 0, 0),
                text_align=TextNode.ALeft,
                parent=button_frame
            )

            # Craft button
            craft_button = DirectButton(
                text="Craft",
                scale=0.04,
                pos=(0.5, 0, 0),
                frameColor=(0.2, 0.6, 0.2, 1.0),
                text_fg=(1, 1, 1, 1),
                relief=DGG.FLAT,
                command=self._craft_recipe,
                extraArgs=[recipe],
                parent=button_frame
            )

            self.recipe_buttons.append({
                'frame': button_frame,
                'button': craft_button,
                'recipe': recipe
            })

    def _get_recipe_description(self, recipe):
        """Generate human-readable description of a recipe."""
        output_block = recipe['output']['block']
        output_count = recipe['output']['count']

        # Map block IDs to names
        block_names = {
            BLOCK_PLANKS: "Oak Planks",
            BLOCK_JUNGLE_PLANKS: "Jungle Planks",
            BLOCK_BIRCH_PLANKS: "Birch Planks",
            BLOCK_STICKS: "Sticks",
            BLOCK_PICKAXE_WOOD: "Wooden Pickaxe",
            BLOCK_PICKAXE_STONE: "Stone Pickaxe",
            BLOCK_PICKAXE_IRON: "Iron Pickaxe",
            BLOCK_AXE_WOOD: "Wooden Axe",
            BLOCK_AXE_STONE: "Stone Axe",
            BLOCK_AXE_IRON: "Iron Axe",
            BLOCK_SHOVEL_WOOD: "Wooden Shovel",
            BLOCK_SHOVEL_STONE: "Stone Shovel",
            BLOCK_SHOVEL_IRON: "Iron Shovel",
            BLOCK_SWORD_WOOD: "Wooden Sword",
            BLOCK_SWORD_STONE: "Stone Sword",
            BLOCK_SWORD_IRON: "Iron Sword",
            BLOCK_CRAFTING_TABLE: "Crafting Table",
            BLOCK_FURNACE: "Furnace",
            BLOCK_CHEST: "Chest",
            BLOCK_WOOD: "Oak Log",
            BLOCK_JUNGLE_LOG: "Jungle Log",
            BLOCK_BIRCH_LOG: "Birch Log",
            BLOCK_COBBLESTONE: "Cobblestone",
            BLOCK_IRON_INGOT: "Iron Ingot",
        }

        output_name = block_names.get(output_block, f"Block {output_block}")
        count_text = f" x{output_count}" if output_count > 1 else ""

        # Add ingredient info
        ingredients = []
        for ingredient_id, count in recipe['ingredients'].items():
            ingredient_name = block_names.get(ingredient_id, f"Block {ingredient_id}")
            ingredients.append(f"{count}x {ingredient_name}")

        ingredient_text = ", ".join(ingredients)
        return f"{output_name}{count_text}  (needs: {ingredient_text})"

    def _craft_recipe(self, recipe):
        """Craft the selected recipe."""
        if self.crafting_system.craft_recipe(recipe, self.current_hotbar):
            # Update hotbar UI
            self.app._update_hotbar_ui()

            # Show success feedback
            output_name = self._get_recipe_description(recipe).split(" ")[0]
            self.app._show_notification(f"Crafted {output_name}!", duration=1.5)

            # Save inventory
            if self.app.save_system is not None and self.app.player is not None:
                self.app.save_system.save_player_data(self.app.player)

            # Refresh menu to show updated recipe availability
            self._refresh_menu()
        else:
            self.app._show_notification("Crafting failed", duration=2.0)

    def _refresh_menu(self):
        """Refresh the menu to show current available recipes."""
        # Get updated available recipes
        available_recipes = self.crafting_system.get_available_recipes(
            self.current_hotbar, self.has_advanced_station
        )

        # Remove old buttons
        for button_data in self.recipe_buttons:
            button_data['frame'].destroy()
        self.recipe_buttons = []

        # Recreate buttons with updated recipes
        self._create_recipe_buttons(available_recipes)


# Global crafting system instance
crafting_system = CraftingSystem()
crafting_menu = None  # Will be initialized when first needed


def open_crafting_menu(app, hotbar, has_advanced_station):
    """
    Global function to open the crafting menu.
    Called from main.py when C key is pressed.
    """
    global crafting_menu

    if crafting_menu is None:
        crafting_menu = CraftingMenu(app)

    available_recipes = crafting_system.get_available_recipes(hotbar, has_advanced_station)
    crafting_menu.show_menu(available_recipes, hotbar, has_advanced_station)
